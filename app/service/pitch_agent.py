import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.pydantic_v1 import PydanticOutputFunctionsParser
# from langchain.chains import LLMChain # Or use LCEL directly
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
# --- CHANGE: Import the updated PitchDeckOutput and FundingStage ---
# ChartData is implicitly included via PitchDeckOutput
from app.schemas.file_schema import PitchDeckOutput, FundingStage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to format retrieved documents
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

class PitchDeckAgent:
    def __init__(self, retriever: VectorStoreRetriever):
        self.retriever = retriever
        self.llm = ChatOpenAI(
            model_name=settings.LLM_MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.2
        )
        self._setup_structured_chain()

    def _setup_structured_chain(self):
        """Sets up the chain for generating structured pitch deck output including chart data."""

        # --- MODIFIED Prompt Template ---
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", """You are an expert AI assistant specializing in creating investor-ready pitch deck outlines from provided company documents.
Your goal is to generate a structured JSON output conforming to the 'PitchDeckOutput' schema based on the retrieved context and user request.

**Instructions:**
1.  Analyze the **Context** below, which contains relevant information extracted from the company's documents.
2.  Address the **User Request**.
3.  Generate content for each section of the pitch deck: **Problem, Solution, Traction, Market, Team, Financials**.
    *   Base the content **strictly** on information found in the **Context**. Do not invent data.
    *   If information for a section is missing in the Context, state "Information not found in provided context." in the 'content' field for that section.
    *   For each section, suggest a relevant **storytelling angle** and a potential **visual aid** (this is separate from the structured chart data).
4.  **Extract Chart Data:**
    *   Carefully scan the **Context** for specific, quantifiable data points suitable for visualization (e.g., user growth numbers over time, revenue figures per quarter/year, market share percentages, key financial metrics).
    *   For each set of related data points found, create a `ChartData` object.
    *   Populate the `labels` list with the corresponding categories or time periods (e.g., ["Q1", "Q2", "Q3"] or ["Jan", "Feb", "Mar"]).
    *   Populate the `values` list with the extracted numerical data (e.g., [1000, 1500, 2200] or [50000, 75000, 110000]). Ensure `labels` and `values` lists have the same number of elements.
    *   Determine the most appropriate `chart_type` ('line', 'bar', 'pie') based on the data pattern (e.g., time series data often uses 'line', comparisons often use 'bar').
    *   Provide a clear `title` for the chart and optional `x_axis_label` and `y_axis_label`.
    *   Add all extracted `ChartData` objects to the `chart_data` list in the final output.
    *   If no suitable quantifiable data for charts is found in the context, return an empty list `[]` for `chart_data`. **Do not invent chart data.**
5.  Develop an **Overall Storytelling Arc** that connects the sections logically and is compelling for investors.
6.  **Tailor** the tone, focus, and depth of information based on the specified **Funding Stage** (Pre-Seed, Seed, Series A) as described previously.
7.  Provide a brief explanation in `funding_stage_tailoring` describing how the output was adjusted for the stage.
8.  Output **only** the structured JSON conforming to the 'PitchDeckOutput' schema, including the populated `chart_data` list.
"""),
                ("human", """**Funding Stage:** {funding_stage}

**User Request:** {user_query}

**Context:**
{context}

**Structured Pitch Deck Output (JSON):**
"""),
            ]
        )
        # --- End Modified Prompt ---

        # Bind the Pydantic model 'PitchDeckOutput' (which now includes ChartData)
        # Use function calling explicitly as recommended before
        structured_llm = self.llm.with_structured_output(
            PitchDeckOutput,
            method="function_calling"
        )

        # Construct the LCEL Chain (using invoke for retriever as recommended)
        self.structured_chain = (
            RunnablePassthrough.assign(
                # Use invoke to address the deprecation warning
                context=lambda inputs: format_docs(self.retriever.invoke(inputs["user_query"]))
            )
            | prompt_template
            | structured_llm
        )
        logger.info("Structured output chain setup complete with chart data extraction.")


    def generate_pitch_deck_report(self, user_query: str, funding_stage: FundingStage) -> PitchDeckOutput:
        """Generates the structured pitch deck report including chart data."""
        logger.info(f"Generating structured pitch deck report with chart data for query: '{user_query}' at stage: {funding_stage}")
        try:
            input_data = {"user_query": user_query, "funding_stage": funding_stage}
            result = self.structured_chain.invoke(input_data)

            if not isinstance(result, PitchDeckOutput):
                 logger.error(f"Chain did not return a PitchDeckOutput object. Got: {type(result)}")
                 raise TypeError("LLM response could not be parsed into the expected PitchDeckOutput structure.")

            # Optional: Log the extracted chart data for debugging
            if result.chart_data:
                logger.info(f"Extracted {len(result.chart_data)} chart data sets.")
                # for chart in result.chart_data:
                #     logger.debug(f"Chart Title: {chart.title}, Type: {chart.chart_type}, Labels: {chart.labels}, Values: {chart.values}")
            else:
                logger.info("No chart data extracted from the context.")


            logger.info("Structured pitch deck report with chart data generated successfully.")
            return result

        except Exception as e:
            logger.error(f"Error during structured pitch deck generation with chart data: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate structured pitch deck with chart data: {e}")