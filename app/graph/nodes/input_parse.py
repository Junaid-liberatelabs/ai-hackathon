# app/graph/nodes/input_parser.py
import logging
import re
from app.graph.state import GraphState
from typing import Any,Dict

logger = logging.getLogger(__name__)

def parse_input_node(state: GraphState) -> Dict[str, Any]:
    """Parses the user input to extract tag and query."""
    logger.info("--- Node: parse_input_node ---")
    user_input = state["user_input"]
    tag = "General" # Default tag
    query = user_input

    # Simple regex to find @Tag at the beginning
    match = re.match(r"^\s*@(\w+)\s*[:\-]?\s*(.*)", user_input, re.IGNORECASE)
    if match:
        parsed = match.group(1).upper()
        if parsed in ["FIR", "CMO", "GENERAL"]:
            tag = parsed if parsed != "GENERAL" else "General" # Normalize
            query = match.group(2).strip()
            logger.info(f"Parsed Tag: {tag}, Query: '{query}'")
        else:
             logger.warning(f"Unknown tag '@{parsed}' found. Treating as General.")
             # Keep original query if tag is unknown
             query = user_input
    else:
         logger.info("No tag found. Defaulting to General.")


    return {"parsed_tag": tag, "query_without_tag": query}