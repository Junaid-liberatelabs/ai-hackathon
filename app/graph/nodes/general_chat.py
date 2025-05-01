# app/graph/nodes/general_chat.py
import logging
from app.graph.state import GraphState
from typing import Any,Dict
from app.service.conversational_logic import get_general_chat_response # Reuse logic

logger = logging.getLogger(__name__)

async def handle_general_chat_node(state: GraphState) -> Dict[str, Any]:
    """Handles general conversation using the conversational logic."""
    logger.info("--- Node: handle_general_chat_node ---")
    # Prepare history including the current user message for the chat function
    current_turn_history = state["conversation_history"] + [
        {"role": "user", "content": state["user_input"]} # Use raw input for chat context
    ]
    try:
        response_text = await get_general_chat_response(current_turn_history)
        return {"final_response": response_text}
    except Exception as e:
        logger.error(f"Error in general chat node: {e}", exc_info=True)
        return {"final_response": "Sorry, I encountered an error while chatting."}