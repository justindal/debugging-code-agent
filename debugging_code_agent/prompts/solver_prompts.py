from typing import Any

ALLOWED_IMPORTS_BLOCK = """import random
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
from math import *"""


def _examples_block(examples: list[dict[str, Any]]) -> str:
    if not examples:
        return "No examples provided."
    lines: list[str] = []
    for idx, example in enumerate(examples, start=1):
        example_input = str(example.get("input", "")).strip()
        example_output = str(example.get("output", "")).strip()
        lines.append(f"Example {idx}:")
        lines.append(f"input: {example_input}")
        lines.append(f"output: {example_output}")
    return "\n".join(lines)


def first_attempt_prompt(
    problem: str,
    entry_point: str,
    starter_code: str,
    examples: list[dict[str, Any]],
) -> str:
    return f"""You are an expert Python programmer. Solve the following problem.

Problem:
{problem}

Examples:
{_examples_block(examples)}

Required callable:
{entry_point}

Starter code (if useful):
{starter_code}

Rules:
- Return ONLY the Python code, nothing else
- Do not include any explanation
- Do not wrap the code in markdown code fences
- Implement the callable referenced in "Required callable"
- Do not print from the solution code
- Standard library imports are allowed when needed
- You may use this import set when helpful:
{ALLOWED_IMPORTS_BLOCK}
- Do not use third-party libraries
- If the problem description restricts imports or specific libraries, follow those restrictions
- Do not add any backticks for formatting
"""


def retry_prompt(
    problem: str,
    entry_point: str,
    starter_code: str,
    examples: list[dict[str, Any]],
    previous_code: str,
    error: str,
    attempt: int,
) -> str:
    return f"""You are an expert Python programmer. Your previous solution had an error.

Problem:
{problem}

Examples:
{_examples_block(examples)}

Required callable:
{entry_point}

Starter code (if useful):
{starter_code}

Your previous code (attempt {attempt}):
{previous_code}

Error output:
{error}

Fix the code so it passes all tests and solves the problem.

Rules:
- Return ONLY the corrected Python code, nothing else
- Do not include any explanation
- Do not wrap the code in markdown code fences
- Keep or implement the callable referenced in "Required callable"
- Address the specific error shown above
- Standard library imports are allowed when needed
- You may use this import set when helpful:
{ALLOWED_IMPORTS_BLOCK}
- Do not use third-party libraries
- If the problem description restricts imports or specific libraries, follow those restrictions
"""
