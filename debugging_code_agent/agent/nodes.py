from collections.abc import Callable

from langchain_ollama import ChatOllama

from debugging_code_agent.agent.execution import PASS_MARKER
from debugging_code_agent.agent.state import AgentState
from debugging_code_agent.prompts.solver_prompts import first_attempt_prompt, retry_prompt


def _emit_test_output(output: str) -> None:
    if not output.strip():
        return
    for line in output.splitlines():
        if (
            line.startswith("[case ")
            or line.startswith("[tests]")
            or line.startswith("  Input:")
            or line.startswith("  Expected:")
            or line.startswith("  Output:")
            or line.startswith("  Error:")
        ):
            print(line)


def _emit_error_output(error: str) -> None:
    stripped = error.strip()
    if not stripped:
        return
    lines = [line for line in stripped.splitlines() if line.strip()]
    if not lines:
        return
    print("[execute] error:")
    for line in lines[:10]:
        print(f"  {line}")
    if len(lines) > 10:
        print("  ...")


def _extract_first_failure_details(output: str) -> str:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("[case ") and "FAILED" in line:
            block = [line]
            cursor = index + 1
            while cursor < len(lines):
                next_line = lines[cursor]
                if next_line.startswith("[case ") or next_line.startswith("[tests]"):
                    break
                if next_line.startswith("  "):
                    block.append(next_line)
                else:
                    break
                cursor += 1
            return "\n".join(block)
    for line in lines:
        if line.startswith("[tests] fatal-error:"):
            return line
    return ""


def llm_call(state: AgentState, model: ChatOllama) -> dict:
    """
    Ask the LLM to write (or rewrite) a Python solution.
    Returns whether we should route to the tool node.
    """
    if state["passed"]:
        print("[graph] solution passed")
        return {"pending_tool": False}

    if state["num_attempts"] >= state["max_attempts"]:
        print(f"[graph] max attempts reached ({state['max_attempts']})")
        return {"pending_tool": False}

    print(f"[write] attempt {state['num_attempts'] + 1}/{state['max_attempts']}")

    if state["num_attempts"] == 0:
        prompt = first_attempt_prompt(
            problem=state["problem"],
            entry_point=state["entry_point"],
            starter_code=state["starter_code"],
            examples=state["examples"],
        )
    else:
        prompt = retry_prompt(
            problem=state["problem"],
            entry_point=state["entry_point"],
            starter_code=state["starter_code"],
            examples=state["examples"],
            previous_code=state["code"] or "",
            error=state["error"] or "",
            attempt=state["num_attempts"],
        )

    response = model.invoke(prompt)
    code = str(response.content).strip()

    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1])

    has_code = bool(code.strip())
    if not has_code:
        print("[write] empty response from model")
        return {
            "code": "",
            "error": "Model returned empty code.",
            "num_attempts": state["num_attempts"] + 1,
            "llm_calls": state.get("llm_calls", 0) + 1,
            "pending_tool": False,
        }

    print("[write] generated a solution!")

    return {
        "code": code,
        "num_attempts": state["num_attempts"] + 1,
        "llm_calls": state.get("llm_calls", 0) + 1,
        "pending_tool": True,
    }


def tool_node(
    state: AgentState,
    tools_by_name: dict[str, Callable[..., dict]],
) -> dict:
    """
    Execute tests against the latest candidate solution.
    """
    if not state.get("pending_tool", False):
        return {}

    result = tools_by_name["run_tests"](
        code=state["code"] or "",
        test_code=state["test_code"],
        entry_point=state["entry_point"],
    )
    _emit_test_output(result["stdout"])
    failure_details = _extract_first_failure_details(result["stdout"])
    stderr_text = result["stderr"].strip()
    if failure_details and stderr_text:
        combined_error = f"{failure_details}\n{stderr_text}"
    elif failure_details:
        combined_error = failure_details
    else:
        combined_error = stderr_text
    if result["stderr"]:
        _emit_error_output(result["stderr"])
    has_no_error = combined_error == ""
    passed = result["return_code"] == 0 and has_no_error and PASS_MARKER in result["stdout"]
    print(f"[evaluate] passed={passed}")
    if not passed and state["num_attempts"] < state["max_attempts"]:
        print(f"[graph] retrying ({state['num_attempts']}/{state['max_attempts']})")

    return {
        "output": result["stdout"],
        "error": combined_error,
        "return_code": result["return_code"],
        "passed": passed,
        "pending_tool": False,
    }
