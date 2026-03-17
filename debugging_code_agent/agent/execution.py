import ast
import os
import subprocess
import sys
import tempfile

PASS_MARKER = "ALL_TESTS_PASSED"
IMPORT_PRELUDE = """import random
import functools
import collections
import string
import math
import datetime

from typing import *
from functools import *
from collections import *
from itertools import *
from heapq import *
from bisect import *
from string import *
from operator import *
from math import *
"""


def _compact_label(text: str, max_chars: int = 100) -> str:
    condensed = " ".join(text.split())
    if len(condensed) <= max_chars:
        return condensed
    return f"{condensed[: max_chars - 3]}..."


class _AssertInstrumenter(ast.NodeTransformer):
    def __init__(self) -> None:
        self.counter = 0

    def _raise_stop_stmt(self) -> ast.Raise:
        return ast.Raise(
            exc=ast.Call(
                func=ast.Name(id="__StopAfterFailure", ctx=ast.Load()),
                args=[],
                keywords=[],
            ),
            cause=None,
        )

    def _record_case_call(
        self,
        index: int,
        input_text: str,
        expected_expr: ast.expr,
        actual_expr: ast.expr,
        passed_expr: ast.expr,
        error_expr: ast.expr,
    ) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id="__record_case", ctx=ast.Load()),
                args=[
                    ast.Constant(value=index),
                    ast.Constant(value=input_text),
                    expected_expr,
                    actual_expr,
                    passed_expr,
                    error_expr,
                ],
                keywords=[],
            )
        )

    def _case_input_text(self, call: ast.Call) -> str:
        parts: list[str] = []
        for idx, arg in enumerate(call.args, start=1):
            parts.append(f"arg{idx}={_compact_label(ast.unparse(arg), max_chars=120)}")
        for keyword in call.keywords:
            if keyword.arg is None:
                parts.append(
                    f"**{_compact_label(ast.unparse(keyword.value), max_chars=120)}"
                )
            else:
                parts.append(
                    f"{keyword.arg}={_compact_label(ast.unparse(keyword.value), max_chars=120)}"
                )
        return ", ".join(parts) if parts else "(no arguments)"

    def _instrument_candidate_assert(
        self, index: int, call: ast.Call, expected_expr: ast.expr
    ) -> list[ast.stmt]:
        expected_name = f"__expected_value_{index}"
        actual_name = f"__actual_value_{index}"
        passed_name = f"__passed_value_{index}"
        input_text = self._case_input_text(call)

        expected_assign = ast.Assign(
            targets=[ast.Name(id=expected_name, ctx=ast.Store())],
            value=expected_expr,
        )
        actual_assign = ast.Assign(
            targets=[ast.Name(id=actual_name, ctx=ast.Store())],
            value=call,
        )
        passed_assign = ast.Assign(
            targets=[ast.Name(id=passed_name, ctx=ast.Store())],
            value=ast.Compare(
                left=ast.Name(id=actual_name, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Name(id=expected_name, ctx=ast.Load())],
            ),
        )
        pass_call = self._record_case_call(
            index=index,
            input_text=input_text,
            expected_expr=ast.Name(id=expected_name, ctx=ast.Load()),
            actual_expr=ast.Name(id=actual_name, ctx=ast.Load()),
            passed_expr=ast.Name(id=passed_name, ctx=ast.Load()),
            error_expr=ast.Constant(value=""),
        )
        stop_if_failed = ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Name(id=passed_name, ctx=ast.Load()),
            ),
            body=[self._raise_stop_stmt()],
            orelse=[],
        )
        fail_call = self._record_case_call(
            index=index,
            input_text=input_text,
            expected_expr=ast.Name(id=expected_name, ctx=ast.Load()),
            actual_expr=ast.Constant(value="<runtime error>"),
            passed_expr=ast.Constant(value=False),
            error_expr=ast.Call(
                func=ast.Name(id="__format_error", ctx=ast.Load()),
                args=[ast.Name(id="exc", ctx=ast.Load())],
                keywords=[],
            ),
        )
        try_stmt = ast.Try(
            body=[actual_assign, passed_assign, pass_call, stop_if_failed],
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id="__StopAfterFailure", ctx=ast.Load()),
                    name=None,
                    body=[ast.Raise(exc=None, cause=None)],
                ),
                ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()),
                    name="exc",
                    body=[fail_call, self._raise_stop_stmt()],
                ),
            ],
            orelse=[],
            finalbody=[],
        )
        return [expected_assign, try_stmt]

    def _instrument_generic_assert(self, index: int, node: ast.Assert) -> list[ast.stmt]:
        actual_name = f"__assert_value_{index}"
        passed_name = f"__assert_passed_{index}"
        input_text = f"assert {_compact_label(ast.unparse(node.test), max_chars=140)}"

        actual_assign = ast.Assign(
            targets=[ast.Name(id=actual_name, ctx=ast.Store())],
            value=node.test,
        )
        passed_assign = ast.Assign(
            targets=[ast.Name(id=passed_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id="bool", ctx=ast.Load()),
                args=[ast.Name(id=actual_name, ctx=ast.Load())],
                keywords=[],
            ),
        )
        pass_call = self._record_case_call(
            index=index,
            input_text=input_text,
            expected_expr=ast.Constant(value=True),
            actual_expr=ast.Name(id=actual_name, ctx=ast.Load()),
            passed_expr=ast.Name(id=passed_name, ctx=ast.Load()),
            error_expr=ast.Constant(value=""),
        )
        stop_if_failed = ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Name(id=passed_name, ctx=ast.Load()),
            ),
            body=[self._raise_stop_stmt()],
            orelse=[],
        )
        fail_call = self._record_case_call(
            index=index,
            input_text=input_text,
            expected_expr=ast.Constant(value=True),
            actual_expr=ast.Constant(value="<runtime error>"),
            passed_expr=ast.Constant(value=False),
            error_expr=ast.Call(
                func=ast.Name(id="__format_error", ctx=ast.Load()),
                args=[ast.Name(id="exc", ctx=ast.Load())],
                keywords=[],
            ),
        )
        try_stmt = ast.Try(
            body=[actual_assign, passed_assign, pass_call, stop_if_failed],
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id="__StopAfterFailure", ctx=ast.Load()),
                    name=None,
                    body=[ast.Raise(exc=None, cause=None)],
                ),
                ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()),
                    name="exc",
                    body=[fail_call, self._raise_stop_stmt()],
                )
            ],
            orelse=[],
            finalbody=[],
        )
        return [try_stmt]

    def visit_Assert(self, node: ast.Assert) -> list[ast.stmt]:
        self.counter += 1
        index = self.counter
        test_expr = node.test
        if (
            isinstance(test_expr, ast.Compare)
            and len(test_expr.ops) == 1
            and isinstance(test_expr.ops[0], ast.Eq)
            and len(test_expr.comparators) == 1
            and isinstance(test_expr.left, ast.Call)
            and isinstance(test_expr.left.func, ast.Name)
            and test_expr.left.func.id == "candidate"
        ):
            return self._instrument_candidate_assert(
                index=index,
                call=test_expr.left,
                expected_expr=test_expr.comparators[0],
            )
        return self._instrument_generic_assert(index=index, node=node)


def _instrument_test_code(test_code: str) -> tuple[str, int]:
    try:
        module = ast.parse(test_code)
    except SyntaxError as exc:
        raise ValueError("Dataset tests have invalid Python syntax.") from exc

    check_function: ast.FunctionDef | None = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "check":
            check_function = node
            break

    if check_function is None:
        raise ValueError("Dataset tests are missing check(candidate).")

    instrumenter = _AssertInstrumenter()
    instrumented_check = instrumenter.visit(check_function)
    for idx, node in enumerate(module.body):
        if node is check_function:
            module.body[idx] = instrumented_check
            break

    ast.fix_missing_locations(module)
    if instrumenter.counter == 0:
        raise ValueError("Dataset check(candidate) contains no assert statements.")

    return ast.unparse(module), instrumenter.counter


def _run_python_script(script: str, timeout: int = 10) -> dict:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "solution.py")

        with open(path, "w") as f:
            f.write(script)

        try:
            result = subprocess.run(
                [sys.executable, path], capture_output=True, text=True, timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "return_code": -1,
            }


def _test_runner_error(message: str) -> dict:
    return {"stdout": "", "stderr": message, "return_code": 1}


def execute_code_against_tests(
    code: str,
    test_code: str,
    entry_point: str,
    timeout: int = 10,
) -> dict:
    if not test_code.strip():
        return _test_runner_error("Dataset test_code is missing.")
    if not entry_point.strip():
        return _test_runner_error("Dataset entry_point is missing.")

    try:
        instrumented_tests = _instrument_test_code(test_code)
    except ValueError as exc:
        return _test_runner_error(str(exc))

    instrumented_test_code, expected_total = instrumented_tests
    test_runner = f"""{IMPORT_PRELUDE}

{code}

{instrumented_test_code}

_EXPECTED_TOTAL = {expected_total}
_CASE_RESULTS = []

class __StopAfterFailure(Exception):
    pass

def __format_value(value, max_chars=220):
    text = value if isinstance(value, str) else repr(value)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."

def __format_error(exc, max_chars=220):
    text = f"{{type(exc).__name__}}: {{exc}}"
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."

def __record_case(index, input_text, expected, actual, passed, error=""):
    status = "PASSED" if passed else "FAILED"
    print(f"[case {{index}}/{{_EXPECTED_TOTAL}}] {{status}}")
    print(f"  Input: {{input_text}}")
    print(f"  Expected: {{__format_value(expected)}}")
    print(f"  Output: {{__format_value(actual)}}")
    if error:
        print(f"  Error: {{__format_value(error)}}")
    _CASE_RESULTS.append(bool(passed))

if __name__ == "__main__":
    candidate = {entry_point}
    check_error = ""
    try:
        check(candidate)
    except __StopAfterFailure:
        pass
    except Exception as exc:
        check_error = __format_error(exc)
        print(f"[tests] fatal-error: {{check_error}}")

    passed = sum(1 for value in _CASE_RESULTS if value)
    total = len(_CASE_RESULTS)
    print(f"[tests] summary: {{passed}}/{{total}} passed")

    if not check_error and total > 0 and passed == total:
        print("{PASS_MARKER}")
    else:
        raise SystemExit(1)
"""
    return _run_python_script(test_runner, timeout=timeout)
