# app/routers/pitch_deck.py
import logging
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Dict, Any, Optional, Union # Ensure Union is imported

# Import necessary schemas
from app.schemas.file_schema import (
    PitchDeckOutput, UploadResponse, FundingStage,
    ChatRequest, GraphChatResponse, ChatTurn # Use GraphChatResponse
)
# Import graph and state definitions
from app.graph.workflow import agent_graph
from app.graph.state import GraphState, FIRSubState
# Import RAG service getter
from app.service.rag_service import get_rag_service # Corrected import path
import uuid
import json # For potential serialization issues

router = APIRouter()
logger = logging.getLogger(__name__)

# --- In-memory storage for FULL graph states ---
# !!! WARNING: Not suitable for production! Use Redis, DB with proper serialization !!!
graph_states: Dict[str, Dict] = {} # Store the full state dict

# --- Updated Chat Endpoint using LangGraph ---
@router.post("/chat", response_model=GraphChatResponse) # Use updated response model
async def graph_chat_endpoint(request: ChatRequest = Body(...)):
    """Handles conversational interaction via the LangGraph agent workflow."""
    conv_id = request.conversation_id
    user_input = request.message
    # --- Get optional doc info ---
    doc_info = request.uploaded_doc_info

    logger.info(f"Processing graph chat message for ConvID: {conv_id}, DocInfo Provided: {doc_info is not None}")

    # 1. Load or initialize graph state
    current_state_dict = graph_states.get(conv_id)
    if current_state_dict is None:
        # Initialize with necessary fields
        current_state_dict = GraphState(
            user_input=user_input,
            conversation_history=[], # History is built turn by turn
            uploaded_doc_info=doc_info, # Store provided doc_info (can be None)
            doc_context=None, # Will be fetched
            parsed_tag="General", # Will be set by parser
            query_without_tag="", # Will be set by parser
            current_funding_stage="Seed", # Default
            fir_state=FIRSubState(generation_requested=False), # Initial FIR state
            final_response=None,
            debug_info={}
        )
        logger.info(f"Initialized new graph state for ConvID: {conv_id}")
    else:
        # Update state for the new turn
        current_state_dict["user_input"] = user_input
        # IMPORTANT: History should reflect state *before* this turn
        # We need to manage history carefully. Let's assume history is stored correctly.
        current_state_dict["uploaded_doc_info"] = doc_info # Update doc info if changed
        # Clear previous turn's output
        current_state_dict["final_response"] = None
        current_state_dict["debug_info"] = {} # Reset debug info
        # Ensure fir_state exists
        if "fir_state" not in current_state_dict:
             current_state_dict["fir_state"] = FIRSubState(generation_requested=False)

        logger.info(f"Loaded existing graph state for ConvID: {conv_id}")

    history_before_current = current_state_dict.get("conversation_history", [])

    # 2. Fetch RAG Context *only if doc_info is provided*
    doc_context = "[No document provided]" # Default context
    if doc_info and "filename" in doc_info:
        logger.info(f"Attempting RAG retrieval for document: {doc_info['filename']}")
        try:
            rag_service = get_rag_service()
            retriever = rag_service.get_retriever(search_kwargs={'k': 7})
            retrieval_query = f"Information relevant to a pitch deck from document {doc_info['filename']}"
            doc_chunks = await retriever.ainvoke(retrieval_query) # Use async invoke
            if doc_chunks:
                doc_context = "\n---\n".join([doc.page_content for doc in doc_chunks])
                logger.info(f"Retrieved {len(doc_chunks)} chunks for ConvID {conv_id}.")
            else:
                logger.warning(f"RAG retrieval returned no chunks for {doc_info['filename']}.")
                doc_context = f"[Document '{doc_info['filename']}' processed, but no relevant text found for query.]"

        except Exception as e:
            logger.error(f"RAG retrieval failed for ConvID {conv_id}: {e}", exc_info=True)
            doc_context = "[Error retrieving document context]"
            # Optionally inform the user via response later?
    else:
         logger.info(f"No document info provided for ConvID {conv_id}, skipping RAG.")

    current_state_dict["doc_context"] = doc_context # Update state with fetched or default context

    # 3. Invoke the LangGraph App
    output_state = None
    try:
        # The input to invoke should match the GraphState structure
        # Pass the whole state dictionary
        config = {"recursion_limit": 15} # Add recursion limit
        output_state = await agent_graph.ainvoke(current_state_dict, config=config)

        if output_state is None:
             raise ValueError("Graph execution returned None state.")

        logger.info(f"Graph execution finished for ConvID: {conv_id}.")

    except Exception as e:
        logger.error(f"Error invoking LangGraph for ConvID {conv_id}: {e}", exc_info=True)
        # Try to salvage state if possible, otherwise respond with error
        final_response_content = "Sorry, an internal error occurred during processing."
        # Check output_state first as it's the result of the latest attempt
        if output_state and output_state.get("final_response"):
            final_response_content = output_state["final_response"]
        elif current_state_dict.get("final_response"): # Fallback to previous state's response if needed
             final_response_content = current_state_dict["final_response"]

        # Save potentially partial state? Risky. Best to log and return error.
        # graph_states[conv_id] = output_state or current_state_dict

        # Raise HTTPException for FastAPI to handle
        raise HTTPException(status_code=500, detail=f"Agent processing error: {e}")


    # 4. Update Conversation History and Save State
    # Add the user message and the final AI response to the history for the *next* turn
    # Ensure history items are compatible with ChatTurn schema (dicts)
    updated_history_dicts = history_before_current + [
        ChatTurn(role="user", content=user_input).dict() # Convert to dict
    ]
    final_response_content = output_state.get("final_response")

    if isinstance(final_response_content, PitchDeckOutput):
        # Store a placeholder or summary in history, not the full object
        updated_history_dicts.append(ChatTurn(role="assistant", content="[Pitch Deck Report Generated]").dict())
    elif isinstance(final_response_content, str):
        updated_history_dicts.append(ChatTurn(role="assistant", content=final_response_content).dict())
    # Handle cases where final_response might be None or other types if necessary

    output_state["conversation_history"] = updated_history_dicts # Save updated history back into state
    graph_states[conv_id] = output_state # Store the complete output state

    # 5. Return Response
    return GraphChatResponse(
        response=final_response_content, # Send the actual content (str or PitchDeckOutput)
        conversation_id=conv_id,
        debug_info=output_state.get("debug_info", {})
    )