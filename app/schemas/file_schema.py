# app/models/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union, Dict, Any

# --- Core Schemas ---
class UploadResponse(BaseModel):
    """Response after successfully uploading and processing a document."""
    filename: str
    message: str
    doc_id: str # Identifier for the processed document

FundingStage = Literal["Pre-Seed", "Seed", "Series A"]
"""Enumeration for the target funding stage."""

class PitchSection(BaseModel):
    """Represents a single standard section of the pitch deck report."""
    title: str = Field(..., description="The title of the section (e.g., 'Problem', 'Solution').")
    content: str = Field(..., description="The main text content for this section, derived from source documents and conversation.")
    storytelling_suggestion: Optional[str] = Field(None, description="A suggestion for a narrative angle or story to use in this section.")
    visual_suggestion: Optional[str] = Field(None, description="A suggestion for a type of visual (chart, image, mockup) to accompany this section. This is separate from the structured chart data.")

class ChartData(BaseModel):
    """Represents structured data extracted for plotting a chart."""
    title: str = Field(..., description="A descriptive title for the chart (e.g., 'Monthly Active Users Growth', 'Revenue by Quarter').")
    chart_type: Literal['line', 'bar', 'pie'] = Field(..., description="The suggested type of chart based on the data (line, bar, or pie).")
    x_axis_label: Optional[str] = Field(None, description="Label for the X-axis (e.g., 'Month', 'Quarter', 'Category').")
    y_axis_label: Optional[str] = Field(None, description="Label for the Y-axis (e.g., 'Number of Users', 'Revenue (USD)').")
    labels: List[str] = Field(..., description="List of labels for the data points (e.g., ['Q1 2023', 'Q2 2023', 'Q3 2023'] or ['Feature A', 'Feature B']).")
    values: List[Union[int, float]] = Field(..., description="List of numerical values corresponding to the labels.")

class PitchDeckOutput(BaseModel):
    """Structured output representing the generated pitch deck report content."""
    problem: PitchSection = Field(..., description="Section defining the customer pain point or market gap.")
    solution: PitchSection = Field(..., description="Section explaining the company's product/service and value proposition.")
    traction: PitchSection = Field(..., description="Section summarizing key achievements, metrics, and milestones.")
    market: PitchSection = Field(..., description="Section describing the target market size, audience, and opportunity.")
    team: PitchSection = Field(..., description="Section summarizing information about the core team and advisors.")
    financials: PitchSection = Field(..., description="Section outlining funding, revenue, projections, or business model.")
    overall_storytelling_arc: str = Field(..., description="A suggested overarching narrative or story connecting the deck sections, tailored to attract investors.")
    chart_data: List[ChartData] = Field([], description="List of structured data sets extracted, suitable for plotting charts.")
    funding_stage_tailoring: str = Field(..., description="Brief explanation of how the content was tailored for the specified funding stage.")

# --- Chat Interaction Schemas ---

class ChatTurn(BaseModel):
    """Represents one turn (user or assistant) in the conversation history."""
    role: Literal["user", "assistant"]
    content: Union[str, Dict[str, Any]] # Allow content to be string or potentially structured dict (like report placeholder)

class ChatRequest(BaseModel):
    """Request model for the /chat endpoint."""
    message: str # The raw user message (e.g., "@FIR Generate report")
    conversation_id: str # Mandatory ID to track conversation state
    uploaded_doc_info: Optional[Dict[str, Any]] = None # Optional document info (filename, doc_id)

class InfoCheckResult(BaseModel):
    """Internal schema for the output of the LLM checking information sufficiency and routing."""
    action: Literal["ask_user", "generate_report", "general_chat"] = Field(..., description="The determined next action.")
    response_text: Optional[str] = Field(None, description="The text to send back to the user (e.g., a question, a chat reply). Required if action is 'ask_user' or 'general_chat'.")
    missing_topics: Optional[List[str]] = Field(default=[], description="Specific topics identified as missing if action is 'ask_user'.")
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the decision.")

# --- ADDED THIS SCHEMA ---
class GraphChatResponse(BaseModel):
    """Response model for the /chat endpoint using the LangGraph workflow."""
    # The actual response content, which could be text or the structured report
    response: Optional[Union[str, PitchDeckOutput]] = None
    conversation_id: str # Return the ID for subsequent calls
    debug_info: Optional[Dict[str, Any]] = None # Optional field for debugging graph steps/logic
# --- END OF ADDED SCHEMA ---