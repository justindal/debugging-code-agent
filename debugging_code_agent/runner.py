from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Mapping
from typing import Any

from debugging_code_agent.agent.graph import build_graph
from debugging_code_agent.agent.state import AgentState
from debugging_code_agent.dataset import get_problems
from debugging_code_agent.selector import Selector
from debugging_code_agent.utils import pick_value

_TEST_SUMMARY_PATTERN = re.compile(r"\[tests\] summary:\s*(\d+)\s*/\s*(\d+)\s*passed")


def _problem_index(records: Iterable[Any]) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        task_id = pick_value(record, "task_id", "id", "_id", default="").strip()
        if task_id:
            indexed[task_id] = record
    return indexed


def _examples(problem: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_examples = problem.get("input_output")
    if not isinstance(raw_examples, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw_examples:
        if isinstance(item, Mapping):
            rows.append(dict(item))
    return rows


def _count_asserts(test_code: str) -> int:
    source = test_code.strip()
    if not source:
        return 0
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source.count("assert")
    return sum(isinstance(node, ast.Assert) for node in ast.walk(tree))


def _compact(text: str, max_chars: int = 120) -> str:
    condensed = " ".join(text.split())
    if len(condensed) <= max_chars:
        return condensed
    return f"{condensed[: max_chars - 3]}..."


def _parse_test_summary(output: str) -> tuple[int, int]:
    for line in reversed(output.splitlines()):
        match = _TEST_SUMMARY_PATTERN.search(line)
        if match:
            return int(match.group(1)), int(match.group(2))
    return 0, 0


def run_problem(
    graph, problem: Mapping[str, Any], max_attempts: int = 5
) -> tuple[AgentState, dict[str, Any]]:
    problem_id = pick_value(problem, "task_id", "id", "_id", default="<unknown>")
    problem_text = pick_value(
        problem,
        "problem_description",
        "description",
        "prompt",
        "question",
        default="",
    )
    entry_point = pick_value(problem, "entry_point", default="")
    starter_code = pick_value(problem, "starter_code", default="")
    test_code = pick_value(problem, "test", default="")
    examples = _examples(problem)
    tests: dict[str, Any] = {"assert_count": _count_asserts(test_code)}
    initial_state: AgentState = {
        "problem": problem_text,
        "entry_point": entry_point,
        "starter_code": starter_code,
        "test_code": test_code,
        "examples": examples,
        "code": None,
        "output": None,
        "error": None,
        "return_code": -1,
        "passed": False,
        "num_attempts": 0,
        "max_attempts": max_attempts,
        "llm_calls": 0,
        "pending_tool": False,
    }

    print(f"\n{'=' * 72}")
    print(f"Problem: {problem_id}")
    print(f"Prompt: {_compact(problem_text)}")

    final_state = graph.invoke(initial_state)
    tests_passed, tests_total = _parse_test_summary(final_state["output"] or "")
    if tests_total == 0 and tests["assert_count"] > 0:
        tests_total = int(tests["assert_count"])
    tests["passed_count"] = tests_passed
    tests["total_count"] = tests_total
    status = "PASS" if final_state["passed"] else "FAIL"
    print(
        "Result: "
        f"{status} | attempts: {final_state['num_attempts']}/{max_attempts}"
    )
    print(f"Tests passed: {tests_passed}/{tests_total}")

    final_error = (final_state["error"] or "").strip()
    if final_error:
        print(f"Last error: {_compact(final_error, max_chars=180)}")

    return final_state, tests


def run_selected_problems(max_attempts: int = 5) -> None:
    problems = get_problems()
    selected = Selector(problems).run()
    selected_ids = [str(task_id) for task_id in (selected or [])]
    if not selected_ids:
        print("No problems selected.")
        return

    problems_by_id = _problem_index(problems)
    graph = build_graph()
    results: list[dict[str, Any]] = []

    for task_id in selected_ids:
        problem = problems_by_id.get(task_id)
        if problem is None:
            print(f"Skipping {task_id}: not found in dataset.")
            continue
        final_state, tests = run_problem(graph, problem, max_attempts=max_attempts)
        results.append(
            {
                "task_id": task_id,
                "passed": final_state["passed"],
                "tests_passed": tests["passed_count"],
                "tests_total": tests["total_count"],
            }
        )

    if not results:
        return

    solved = sum(1 for item in results if item["passed"])
    tests_passed_total = sum(int(item["tests_passed"]) for item in results)
    tests_total = sum(int(item["tests_total"]) for item in results)
    failed = [str(item["task_id"]) for item in results if not item["passed"]]

    print(f"\n{'=' * 72}")
    print("Run summary")
    print(f"Solved: {solved}/{len(results)}")
    print(f"Assertion tests passed: {tests_passed_total}/{tests_total}")
    if failed:
        print(f"Failed tasks: {', '.join(failed)}")
