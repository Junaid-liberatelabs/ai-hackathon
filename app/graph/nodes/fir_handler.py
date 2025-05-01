# app/graph/nodes/fir_handler.py
import logging
from typing import Dict, Any
from app.graph.state import GraphState, FIRSubState
from app.service.conversational_logic import check_info_and_route, generate_pitch_deck_report
from app.schemas.file_schema import PitchDeckOutput, FundingStage

logger = logging.getLogger(__name__)

async def handle_fir_node(state: GraphState) -> Dict[str, Any]:
    """Handles FIR requests, managing the pitch deck generation conversation."""
    logger.info("--- Node: handle_fir_node ---")
    doc_context = state.get("doc_context", "[Document context not available]")
    # History includes turns *before* the current user message triggering this node
    history_before_current = state["conversation_history"]
    # Add the current user query (without tag) to represent the latest input for FIR logic
    current_fir_input_turn = {"role": "user", "content": state["query_without_tag"]}
    fir_context_history = history_before_current + [current_fir_input_turn]

    # Get current FIR sub-state
    fir_state = state.get("fir_state", FIRSubState(generation_requested=False)) # Initialize if missing

    # Determine funding stage (can be passed in state or default)
    funding_stage = state.get("current_funding_stage", "Seed")

    final_response: Any = None
    updated_fir_state = fir_state.copy() # Work on a copy
    updated_fir_state["intermediate_message"] = None # Clear previous intermediate message
    updated_fir_state["generated_report"] = None # Clear previous report

    try:
        # Call the checking/routing logic (passing relevant history and context)
        # This logic now determines if we ask, generate, or maybe even handle sub-chat within FIR
        route_result = await check_info_and_route(
            conversation_history=fir_context_history, # Pass history relevant to FIR
            doc_context=doc_context,
            funding_stage=funding_stage
        )

        action = route_result.action
        state["debug_info"].update({ # Add debug info from check
             "fir_check_action": action,
             "fir_check_reasoning": route_result.reasoning,
             "fir_check_missing": route_result.missing_topics
        })

        if action == "ask_user":
            logger.info("FIR Action: Ask User")
            updated_fir_state["missing_topics"] = route_result.missing_topics
            updated_fir_state["intermediate_message"] = route_result.response_text
            final_response = route_result.response_text # Pass question back to user
            updated_fir_state["generation_requested"] = False # Wait for answer

        elif action == "generate_report":
            logger.info("FIR Action: Generate Report")
            # Ensure generation was intended (e.g., user explicitly asked or provided final info)
            # The check_info_and_route logic should ideally handle this intent check.
            report = await generate_pitch_deck_report(
                doc_context=doc_context,
                conversation_history=fir_context_history, # Pass full relevant history
                funding_stage=funding_stage
            )
            updated_fir_state["generated_report"] = report
            final_response = report # Pass the full report object back
            updated_fir_state["generation_requested"] = False # Reset after generation
            updated_fir_state["missing_topics"] = None

        elif action == "general_chat":
             # This might happen if the user says "@FIR Thanks!"
             # We could have a simple FIR-context chat response here
             logger.info("FIR Action: General Chat within FIR context")
             # Use the response from the checker if appropriate, or generate a new one
             response = route_result.response_text or "Okay, let me know when you're ready to continue with the pitch deck."
             final_response = response
             updated_fir_state["intermediate_message"] = response


    except Exception as e:
        logger.error(f"Error in FIR node processing: {e}", exc_info=True)
        final_response = "Sorry, I encountered an error while handling your request for the pitch deck."
        updated_fir_state["intermediate_message"] = final_response

    # Return the updated FIR sub-state and the final response for this turn
    return {"fir_state": updated_fir_state, "final_response": final_response}