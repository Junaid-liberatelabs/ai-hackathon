# app/services/conversational_logic.py
import logging
from typing import List, Dict, Any, Tuple, Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field # Use v1 for compatibility if needed

# Import necessary schemas and services
from app.schemas.file_schema import PitchDeckOutput, FundingStage, InfoCheckResult, ChatTurn
from app.service.rag_service import get_rag_service # Import the function to get the service instance
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LLM Instances ---
# LLM for checking/routing/chatting
routing_llm = ChatOpenAI(model=settings.LLM_MODEL_NAME, temperature=0.4, openai_api_key=settings.OPENAI_API_KEY)
# LLM for structured report generation
generator_llm = ChatOpenAI(model=settings.LLM_MODEL_NAME, temperature=0.1, openai_api_key=settings.OPENAI_API_KEY)

# --- Core Logic Functions ---

async def check_info_and_route(
    conversation_history: List[Dict[str, Any]], # Expect list of dicts matching ChatTurn
    doc_context: str,
    funding_stage: FundingStage = "Seed"
) -> InfoCheckResult:
    """
    Uses LLM to check info sufficiency based on doc context and conversation history,
    and determines the next action (ask user, generate, or general chat).
    """
    logger.info("Checking info sufficiency and routing...")

    # Prepare history for the prompt using BaseMessage types
    prompt_history: List[BaseMessage] = []
    for turn in conversation_history:
        # Ensure content is treated as string for history messages
        content_str = str(turn.get('content', '')) # Handle potential dicts/None safely
        if turn.get('role') == "user":
            prompt_history.append(HumanMessage(content=content_str))
        elif turn.get('role') == "assistant":
            # Avoid adding report placeholders to LLM history if they exist
            if content_str != "[Pitch Deck Report Generated]":
                 prompt_history.append(AIMessage(content=content_str))

    # Define the prompt for the LLM
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an AI assistant helping a user create a pitch deck (target stage: {funding_stage}). Your goal is to determine the next step based on the conversation history and provided document context.

        **Required Pitch Deck Sections:** Problem, Solution, Traction, Market, Team, Financials.

        **Analyze:**
        1.  **Document Context:** Key information extracted from the user's uploaded document. *Note: This might be empty, indicate no document was provided, or indicate an error.*
        2.  **Conversation History:** The ongoing dialogue with the user. Pay attention to the *last user message* in the history provided.

        **Determine the Next Action:**
        1.  **Is the user explicitly asking to generate the report NOW in their *last* message?** (e.g., "generate the report", "create the deck now", "make the pitch deck")
        2.  **Was the *previous* AI message asking for specific information?** If yes, assume the user's latest message is an attempt to provide that information.
        3.  **If asking for generation OR providing info:** Check if you have *sufficient detail* across MOST of the required sections (Problem, Solution, Traction, Market, Team are key) by combining the Document Context (if available and relevant) and Conversation History. *If no document context exists or is relevant, sufficiency relies heavily on the conversation.* Financials might be less detailed initially.
            *   If **SUFFICIENT**: Set action to `generate_report`. Provide brief reasoning.
            *   If **INSUFFICIENT** (especially if no document context): Set action to `ask_user`. Identify the *most critical* missing topics needed to start (e.g., 'Company name and core idea', 'The main problem you solve', 'Your target customer'). Formulate a *single, concise question* asking for this missing info in `response_text`. Provide reasoning.
        4.  **If NEITHER asking for generation NOR providing info:** Assume it's general conversation. Set action to `general_chat`. Formulate a helpful, conversational reply in `response_text` based on the last user message and history.

        **Respond ONLY with the JSON schema `InfoCheckResult`.**
        """),
        MessagesPlaceholder(variable_name="history"), 
        ("human", f"""**Document Context:**
        ```
        {doc_context}
        ```

        **Based on the Document Context and the full Conversation History (especially the last user message), determine the next action and respond in the required JSON format.**
        """)
    ])

    # Chain for structured output
    checker_chain = prompt | routing_llm.with_structured_output(InfoCheckResult, method="function_calling")

    try:
        # Pass the prepared history
        result: InfoCheckResult = await checker_chain.ainvoke({"history": prompt_history})
        logger.info(f"Routing/Check Result: Action={result.action}, Missing={result.missing_topics}, Reasoning={result.reasoning}")
        return result
    except Exception as e:
        logger.error(f"Error during info check/routing LLM call: {e}", exc_info=True)
        # Fallback response
        return InfoCheckResult(
            action="general_chat",
            response_text="Sorry, I had trouble understanding that. Could you please rephrase or tell me what you'd like to do next?",
            reasoning="Error in processing."
        )


async def generate_pitch_deck_report(
    doc_context: str,
    conversation_history: List[Dict[str, Any]], # Expect list of dicts matching ChatTurn
    funding_stage: FundingStage = "Seed"
) -> PitchDeckOutput:
    """Generates the final pitch deck report using document context and conversation history."""
    logger.info(f"Generating final pitch deck report for stage: {funding_stage}")

    # Format conversation history as additional context, excluding placeholders
    history_items = []
    for turn in conversation_history:
        content_str = str(turn.get('content', ''))
        if content_str != "[Pitch Deck Report Generated]": # Exclude placeholder
             history_items.append(f"{turn.get('role', 'unknown').capitalize()}: {content_str}")

    history_str = "\n".join(history_items)
    full_context = f"## Source Document Context:\n{doc_context}\n\n## Conversation History (provides additional user input/clarifications):\n{history_str}"

    # Prepare Prompt for Final Generation
    generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert AI assistant creating an investor-ready pitch deck outline.
Generate a structured JSON output conforming to the 'PitchDeckOutput' schema.

**Instructions:**
1.  Analyze the **Combined Context** below (Document Context + Conversation History). *If Document Context indicates no document was provided, is empty, or errored, rely primarily on the Conversation History.* Use information from the conversation to supplement or clarify document info if available.
2.  Generate content for each section: Problem, Solution, Traction, Market, Team, Financials, based **strictly** on the Combined Context. Do not invent data. State "Information not found" if details are missing.
3.  Suggest storytelling angles and visual aids.
4.  Extract quantifiable data points from the **Combined Context** to populate `chart_data` (labels, values, type, title). Return empty list if no suitable data exists.
5.  Develop an Overall Storytelling Arc.
6.  Tailor the output for the specified **Funding Stage**.
7.  Provide the `funding_stage_tailoring` explanation.
8.  Output **only** the structured JSON conforming to the 'PitchDeckOutput' schema."""),
            ("human", f"""**Funding Stage:** {funding_stage}

**Combined Context:**
{full_context}

**User Request:** Generate the pitch deck report based on all available information.

**Structured Pitch Deck Output (JSON):**
"""),
        ])

    # Chain for structured output
    generator_chain = generation_prompt | generator_llm.with_structured_output(PitchDeckOutput, method="function_calling")

    try:
        report: PitchDeckOutput = await generator_chain.ainvoke({})
        logger.info("Successfully generated final pitch deck report.")
        return report
    except Exception as e:
        logger.error(f"Error during final report generation LLM call: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate pitch deck report: {e}")


async def get_general_chat_response(conversation_history: List[Dict[str, Any]]) -> str: # Expect list of dicts
    """Generates a simple conversational response."""
    logger.info("Generating general chat response...")

    # Prepare history using BaseMessage types, excluding placeholders
    prompt_history: List[BaseMessage] = []
    for turn in conversation_history:
        content_str = str(turn.get('content', ''))
        if content_str == "[Pitch Deck Report Generated]": continue # Skip placeholder

        if turn.get('role') == "user":
            prompt_history.append(HumanMessage(content=content_str))
        elif turn.get('role') == "assistant":
            prompt_history.append(AIMessage(content=content_str))


    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful and friendly AI assistant. Respond conversationally to the user's latest message, keeping the overall context of helping with a pitch deck in mind."),
        MessagesPlaceholder(variable_name="history")
    ])

    chain = prompt | routing_llm # Use the conversational LLM

    try:
        response = await chain.ainvoke({"history": prompt_history})
        return response.content
    except Exception as e:
        logger.error(f"Error during general chat LLM call: {e}", exc_info=True)
        return "Sorry, I encountered an issue responding. Could you try again?"