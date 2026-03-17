from typing import Any, Optional, TypedDict


class AgentState(TypedDict):
    problem: str
    entry_point: str
    starter_code: str
    test_code: str
    examples: list[dict[str, Any]]
    code: Optional[str]
    output: Optional[str]
    error: Optional[str]
    return_code: int
    passed: bool
    num_attempts: int
    max_attempts: int
    llm_calls: int
    pending_tool: bool
