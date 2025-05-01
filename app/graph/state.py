# app/graph/state.py
from typing import List, TypedDict, Optional, Dict,Literal,Union,Any
from app.schemas.file_schema import ChatTurn, PitchDeckOutput # Use ChatTurn from previous step

class FIRSubState(TypedDict):
    """State specific to the FIR/Pitch Deck generation process."""
    # Information needed based on the last check
    missing_topics: Optional[List[str]] = None
    # Flag to indicate if generation should proceed if info is sufficient
    generation_requested: bool = False
    # The final generated report for this turn
    generated_report: Optional[PitchDeckOutput] = None
    # Any intermediate message from the FIR process (e.g., asking a question)
    intermediate_message: Optional[str] = None

class GraphState(TypedDict):
    """Represents the overall state of the conversational graph."""
    # Input/Context
    user_input: str                 # The raw message from the user (e.g., "@FIR Generate report")
    conversation_history: List[ChatTurn] # Full history up to the *previous* turn
    uploaded_doc_info: Dict[str, Any] # Info about the uploaded doc (filename, doc_id)
    doc_context: Optional[str] = None # Context retrieved via RAG for this turn

    # Routing/Processing Info
    parsed_tag: Literal["FIR", "CMO", "General"] # Tag extracted from user_input
    query_without_tag: str          # User input after removing the tag
    current_funding_stage: str = "Seed" # Default, can be updated

    # Sub-process State
    fir_state: FIRSubState          # Nested state for FIR process

    # Output
    final_response: Optional[Union[str, PitchDeckOutput]] = None # Final output for the user this turn
    debug_info: Dict[str, Any] = {} # For debugging steps