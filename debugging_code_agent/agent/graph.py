from typing import Literal

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from debugging_code_agent.agent.execution import execute_code_against_tests
from debugging_code_agent.agent.nodes import llm_call, tool_node
from debugging_code_agent.agent.state import AgentState


def should_continue(state: AgentState) -> Literal["tool_node", "__end__"]:
    """
    Route to tool execution or end the workflow.
    """
    if state.get("pending_tool", False):
        return "tool_node"
    return END


def build_graph(model: str = "llama3.1", temperature: float = 0.1):
    """
    Build and compile the agent graph.
    """
    model_client = ChatOllama(model=model, temperature=temperature)
    tools_by_name = {
        "run_tests": execute_code_against_tests,
    }

    def llm_call_node(state: AgentState) -> dict:
        return llm_call(state=state, model=model_client)

    def tool_node_call(state: AgentState) -> dict:
        return tool_node(state=state, tools_by_name=tools_by_name)

    agent_builder = StateGraph(AgentState)

    agent_builder.add_node("llm_call", llm_call_node)
    agent_builder.add_node("tool_node", tool_node_call)

    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END],
    )
    agent_builder.add_edge("tool_node", "llm_call")

    agent = agent_builder.compile()
    return agent
