from typing import Any

SYSTEM_PROMPT = (
    "You are an expert Python programmer specialising in algorithmic problem solving.\n\n"
    "When given a problem, return only the completed Python solution. "
    "No explanation, no markdown, no code fences.\n\n"
    "You may only use the following imports — do not add any others:\n\n"
    "import random\nimport functools\nimport collections\nimport string\n"
    "import math\nimport datetime\nimport sys\nimport re\nimport copy\nimport queue\n\n"
    "from typing import *\nfrom functools import *\nfrom collections import *\n"
    "from itertools import *\nfrom heapq import *\nfrom bisect import *\n"
    "from string import *\nfrom operator import *\nfrom math import *"
)


def first_attempt_prompt(
    problem: str,
    starter_code: str,
    difficulty: str = "",
    tags: str = "",
    **_kwargs: Any,
) -> str:
    difficulty_text = difficulty or "Unknown"
    topics_text = tags or "Unknown"
    return (
        f"Difficulty: {difficulty_text}\n"
        f"Topics: {topics_text}\n\n"
        f"Problem:\n{problem.strip()}\n\n"
        f"Starter code:\n{starter_code}"
    )
