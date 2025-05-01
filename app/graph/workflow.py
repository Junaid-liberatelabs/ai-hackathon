# app/graph/workflow.py
import logging
from langgraph.graph import StateGraph, END, START
from app.graph.state import GraphState

# Import node functions
from app.graph.nodes.input_parse import parse_input_node
from app.graph.nodes.general_chat import handle_general_chat_node
from app.graph.nodes.cmo_handler import handle_cmo_node
from app.graph.nodes.fir_handler import handle_fir_node
from app.graph.nodes.output_formatter import prepare_final_response_node

logger = logging.getLogger(__name__)

def route_based_on_tag(state: GraphState):
    """Conditional edge routing based on the parsed tag."""
    tag = state.get("parsed_tag", "General")
    logger.info(f"Routing based on tag: {tag}")
    if tag == "FIR":
        return "handle_fir_request"
    elif tag == "CMO":
        return "handle_cmo_request"
    else: # General
        return "handle_general_chat"

def create_agent_workflow():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_input", parse_input_node)
    workflow.add_node("handle_general_chat", handle_general_chat_node)
    workflow.add_node("handle_cmo_request", handle_cmo_node)
    workflow.add_node("handle_fir_request", handle_fir_node)
    workflow.add_node("prepare_output", prepare_final_response_node) # Optional output node

    # Define edges
    workflow.add_edge(START, "parse_input") # Start by parsing

    # Conditional routing after parsing
    workflow.add_conditional_edges(
        "parse_input",
        route_based_on_tag,
        {
            "handle_general_chat": "handle_general_chat",
            "handle_cmo_request": "handle_cmo_request",
            "handle_fir_request": "handle_fir_request",
        }
    )

    # Edges leading to the output preparation/end
    workflow.add_edge("handle_general_chat", "prepare_output")
    workflow.add_edge("handle_cmo_request", "prepare_output")
    workflow.add_edge("handle_fir_request", "prepare_output")

    workflow.add_edge("prepare_output", END) # End after preparing output

    # Compile the graph
    app = workflow.compile()
    logger.info("LangGraph workflow compiled successfully.")
    return app

# Create a singleton instance of the compiled graph
agent_graph = create_agent_workflow()