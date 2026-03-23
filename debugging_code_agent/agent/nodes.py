from collections.abc import Callable
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from debugging_code_agent.agent.execution import PASS_MARKER
from debugging_code_agent.agent.state import AgentState
from debugging_code_agent.prompts.solver_prompts import (
    SYSTEM_PROMPT,
    first_attempt_prompt,
)

_LIST_TYPE = (list, tuple)

_FENCED_CODE_BLOCK = re.compile(r"```(?:python|py)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_MAX_FEEDBACK_CASES = 3
_TEMP_SCHEDULE = (0.1, 0.3, 0.5, 0.7, 0.9)


def _extract_test_summary(output: str) -> str:
    for line in reversed(output.splitlines()):
        if line.startswith("[tests] summary:"):
            return line
    return ""


def _emit_generated_code(code: str, attempt: int) -> None:
    print(f"[write] generated code (attempt {attempt}):")
    print("-" * 72)
    print(code.rstrip())
    print("-" * 72)


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


def _extract_failure_blocks(output: str, max_cases: int = _MAX_FEEDBACK_CASES) -> list[str]:
    lines = output.splitlines()
    blocks: list[str] = []
    idx = 0
    while idx < len(lines) and len(blocks) < max_cases:
        line = lines[idx]
        if line.startswith("[case ") and "FAILED" in line:
            block = [line]
            cursor = idx + 1
            while cursor < len(lines):
                next_line = lines[cursor]
                if next_line.startswith("[case ") or next_line.startswith("[tests]"):
                    break
                if next_line.startswith("  "):
                    block.append(next_line)
                else:
                    break
                cursor += 1
            blocks.append("\n".join(block))
            idx = cursor
        elif line.startswith("[tests] fatal-error:"):
            blocks.append(line)
            idx += 1
        else:
            idx += 1
    return blocks


def _normalize_model_code(content: str) -> str:
    text = _THINK_BLOCK.sub("", content).strip()
    fenced = _FENCED_CODE_BLOCK.search(text)
    if fenced:
        return fenced.group(1).strip()
    return text


def _emit_compact_test_report(
    output: str,
    failure_blocks: list[str],
    stderr_text: str,
) -> None:
    summary = _extract_test_summary(output)
    if summary:
        print(summary)

    if failure_blocks:
        print("[tests] first failure:")
        for line in failure_blocks[0].splitlines():
            print(line)

    if stderr_text:
        _emit_error_output(stderr_text)


def _build_feedback_message(output: str, failure_blocks: list[str], stderr: str) -> str:
    summary = _extract_test_summary(output)
    parts: list[str] = ["Your solution is incorrect."]
    if summary:
        parts.append(summary)
    if failure_blocks:
        parts.append("")
        for block in failure_blocks:
            parts.append(block)
    if stderr:
        parts.append(stderr)
    parts.append("")
    parts.append("Carefully re-read the problem. Your approach may be fundamentally wrong.")
    parts.append("Write a corrected solution.")
    return "\n".join(parts)


def _attempt_temperature(attempt: int) -> float:
    idx = min(attempt, len(_TEMP_SCHEDULE) - 1)
    return _TEMP_SCHEDULE[idx]


def llm_call(state: AgentState, model: BaseChatModel) -> dict:
    if state["passed"]:
        print("[graph] solution passed")
        return {"pending_tool": False}

    if state["num_attempts"] >= state["max_attempts"]:
        print(f"[graph] max attempts reached ({state['max_attempts']})")
        return {"pending_tool": False}

    attempt = state["num_attempts"] + 1
    temp = _attempt_temperature(state["num_attempts"])
    print(f"[write] attempt {attempt}/{state['max_attempts']} (temp={temp})")

    new_messages: list = []

    if state["num_attempts"] == 0:
        raw_tags = state.get("tags", "")
        if isinstance(raw_tags, _LIST_TYPE):
            tags_str = ", ".join(raw_tags) if raw_tags else "Unknown"
        else:
            tags_str = raw_tags or "Unknown"

        user_text = first_attempt_prompt(
            problem=state["problem"],
            starter_code=state["starter_code"],
            difficulty=state.get("difficulty", ""),
            tags=tags_str,
        )
        new_messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ]

    all_messages = state.get("messages", []) + new_messages

    original_temp = getattr(model, "temperature", None)
    try:
        model.temperature = temp
        response = model.invoke(all_messages)
    finally:
        if original_temp is not None:
            model.temperature = original_temp

    code = _normalize_model_code(str(response.content))

    has_code = bool(code.strip())
    if not has_code:
        print("[write] empty response from model")
        return {
            "messages": new_messages + [AIMessage(content="")],
            "code": "",
            "error": "Model returned empty code.",
            "num_attempts": attempt,
            "llm_calls": state.get("llm_calls", 0) + 1,
            "pending_tool": False,
        }

    _emit_generated_code(code=code, attempt=attempt)

    return {
        "messages": new_messages + [AIMessage(content=str(response.content))],
        "code": code,
        "num_attempts": attempt,
        "llm_calls": state.get("llm_calls", 0) + 1,
        "pending_tool": True,
    }


def tool_node(
    state: AgentState,
    tools_by_name: dict[str, Callable[..., dict]],
) -> dict:
    if not state.get("pending_tool", False):
        return {}

    result = tools_by_name["run_tests"](
        code=state["code"] or "",
        test_code=state["test_code"],
        entry_point=state["entry_point"],
    )
    failure_blocks = _extract_failure_blocks(result["stdout"])
    stderr_text = result["stderr"].strip()
    _emit_compact_test_report(
        output=result["stdout"],
        failure_blocks=failure_blocks,
        stderr_text=stderr_text,
    )
    first_failure = failure_blocks[0] if failure_blocks else ""
    if first_failure and stderr_text:
        combined_error = f"{first_failure}\n{stderr_text}"
    elif first_failure:
        combined_error = first_failure
    else:
        combined_error = stderr_text
    has_no_error = combined_error == ""
    passed = result["return_code"] == 0 and has_no_error and PASS_MARKER in result["stdout"]
    print(f"[evaluate] passed={passed}")

    updates: dict = {
        "output": result["stdout"],
        "error": combined_error,
        "return_code": result["return_code"],
        "passed": passed,
        "pending_tool": False,
    }

    if not passed and state["num_attempts"] < state["max_attempts"]:
        print(f"[graph] retrying ({state['num_attempts']}/{state['max_attempts']})")
        feedback = _build_feedback_message(result["stdout"], failure_blocks, stderr_text)
        updates["messages"] = [HumanMessage(content=feedback)]

    return updates
