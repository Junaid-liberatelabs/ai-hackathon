# app/graph/nodes/output_formatter.py
import logging
from app.graph.state import GraphState
from typing import Dict,Any

logger = logging.getLogger(__name__)

def prepare_final_response_node(state: GraphState) -> Dict[str, Any]:
    """Ensures the final_response is ready."""
    # This node might become more complex if formatting is needed
    # For now, it just confirms the final_response is set by previous nodes
    logger.info("--- Node: prepare_final_response_node ---")
    if state.get("final_response") is None:
         logger.warning("Final response was not set by upstream nodes!")
         # Provide a fallback response
         return {"final_response": "Sorry, I reached the end of my process without a clear response."}
    # No change needed if final_response is already set correctly
    return {}