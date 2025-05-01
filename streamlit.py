# streamlit.py
import streamlit as st
import requests
import pandas as pd
import altair as alt
import io
import json
import uuid
from typing import Dict, Any, Optional # Import typing helpers

# --- Configuration ---
FASTAPI_BASE_URL = "http://127.0.0.1:8000" # Adjust if your backend runs elsewhere
UPLOAD_ENDPOINT = f"{FASTAPI_BASE_URL}/documents/upload"
CHAT_ENDPOINT = f"{FASTAPI_BASE_URL}/pitch/chat" # Use the graph chat endpoint

# --- Helper Functions ---

def upload_file_to_backend(uploaded_file_obj):
    """Sends the uploaded file to the FastAPI backend."""
    if uploaded_file_obj is not None:
        files = {'file': (uploaded_file_obj.name, uploaded_file_obj.getvalue(), uploaded_file_obj.type)}
        try:
            response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=60)
            response.raise_for_status()
            return response.json() # Expects UploadResponse schema
        except requests.exceptions.RequestException as e:
            st.error(f"Error uploading file: {e}")
            try:
                error_detail = response.json().get("detail", str(e))
                st.error(f"Backend Upload Error Detail: {error_detail}")
            except: pass
            return None
        except json.JSONDecodeError:
            st.error(f"Failed to decode JSON response from upload endpoint. Response text: {response.text}")
            return None
    return None

def send_chat_message_to_backend(message: str, conversation_id: str, uploaded_doc_info: Optional[Dict[str, Any]]): # Allow None
    """Sends a message to the conversational agent backend."""
    payload = {
        "message": message,
        "conversation_id": conversation_id,
        "uploaded_doc_info": uploaded_doc_info # Pass None if no doc uploaded
    }
    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=300) # Long timeout for LLM/Graph
        response.raise_for_status()
        return response.json() # Expects GraphChatResponse schema
    except requests.exceptions.RequestException as e:
        st.error(f"Error sending message: {e}")
        try:
            error_detail = response.json().get("detail", str(e))
            st.error(f"Backend Chat Error Detail: {error_detail}")
        except: pass
        return None
    except json.JSONDecodeError:
        st.error(f"Failed to decode JSON response from chat endpoint. Response text: {response.text}")
        return None

# --- Display Functions (display_chart, display_pitch_deck_report) ---
def display_chart(chart_info):
    """Displays a chart based on the extracted data using Streamlit/Altair."""
    title = chart_info.get('title', 'Untitled Chart')
    chart_type = chart_info.get('chart_type', 'bar')
    labels = chart_info.get('labels', [])
    values = chart_info.get('values', [])
    x_label = chart_info.get('x_axis_label')
    y_label = chart_info.get('y_axis_label')

    if not labels or not values or len(labels) != len(values):
        st.warning(f"Incomplete or mismatched data for chart: '{title}'")
        return

    try:
        df = pd.DataFrame({'Label': labels, 'Value': values})
    except Exception as e:
        st.warning(f"Could not create DataFrame for chart '{title}': {e}")
        return

    st.write(f"**📊 {title}**")
    try:
        if chart_type == 'line':
            df_plot = df.set_index('Label')
            st.line_chart(df_plot)
        elif chart_type == 'bar':
            df_plot = df.set_index('Label')
            st.bar_chart(df_plot)
        elif chart_type == 'pie':
             base = alt.Chart(df).encode(theta=alt.Theta(field="Value", type="quantitative", stack=True))
             pie = base.mark_arc(outerRadius=120).encode(
                  color=alt.Color(field="Label", type="nominal"),
                  order=alt.Order(field="Value", sort="descending"),
                  tooltip=['Label', 'Value']
             )
             st.altair_chart(pie, use_container_width=True)
        else:
            st.write(f"(Unsupported chart type: {chart_type})")
        if x_label and chart_type in ['line', 'bar']: st.caption(f"X-axis: {x_label}")
        if y_label and chart_type in ['line', 'bar']: st.caption(f"Y-axis: {y_label}")
    except Exception as e:
        st.error(f"Error displaying chart '{title}': {e}")
    st.divider()


def display_pitch_deck_report(report_dict):
    """Formats and displays the structured pitch deck report from a dictionary."""
    if not report_dict:
        st.warning("No report data to display.")
        return

    pitch_deck = report_dict

    st.markdown("## Pitch Deck Report")
    st.markdown(f"*(Tailored for: **{pitch_deck.get('funding_stage_tailoring', 'N/A')}**)*")
    st.divider()

    sections = ["problem", "solution", "traction", "market", "team", "financials"]
    section_emojis = {"problem": "❓", "solution": "💡", "traction": "📈", "market": "🎯", "team": "👥", "financials": "💰"}

    for section_key in sections:
        section_data = pitch_deck.get(section_key)
        if section_data:
            emoji = section_emojis.get(section_key, "")
            st.markdown(f"### {emoji} {section_data.get('title', section_key.capitalize())}")
            st.markdown(section_data.get('content', "_No content provided._"))
            if section_data.get('storytelling_suggestion'):
                st.markdown(f"**Storytelling Suggestion:** *{section_data['storytelling_suggestion']}*")
            if section_data.get('visual_suggestion'):
                st.markdown(f"**Visual Suggestion:** *{section_data['visual_suggestion']}*")
            st.markdown("---")

    st.markdown("### 📜 Overall Storytelling Arc")
    st.markdown(pitch_deck.get('overall_storytelling_arc', "_No overall arc provided._"))
    st.markdown("---")

    chart_data_list = pitch_deck.get("chart_data", [])
    if chart_data_list:
        st.markdown("## Extracted Chart Data")
        st.markdown("---")
        for chart_info in chart_data_list:
            display_chart(chart_info)
    else:
        st.info("No specific chart data was extracted.")


# --- Streamlit App ---

st.set_page_config(page_title="Agent Workflow Pitch Deck Generator", layout="wide")
st.title("🚀 AI Pitch Deck Assistant (Agent Workflow)")
st.caption("Use tags like @FIR, @CMO, or @General (default) to direct your request. Document upload is optional.")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_file_info" not in st.session_state:
    st.session_state.uploaded_file_info = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# --- File Upload Section ---
with st.sidebar:
    st.header("1. Upload Document (Optional)")
    uploaded_file = st.file_uploader(
        "Choose a PDF, DOCX, or PPTX file",
        type=["pdf", "docx", "pptx"],
        accept_multiple_files=False
    )

    if uploaded_file is not None:
        # Process button appears if a file is selected
        if st.button(f"Process '{uploaded_file.name}'"):
            with st.spinner("Uploading and processing file..."):
                upload_response = upload_file_to_backend(uploaded_file)
                if upload_response and "filename" in upload_response and "doc_id" in upload_response:
                    # --- MODIFICATION START ---
                    # Check if it's a *different* file than already processed
                    is_new_file = (st.session_state.uploaded_file_info is None or
                                   st.session_state.uploaded_file_info.get("filename") != upload_response['filename'])

                    st.session_state.uploaded_file_info = upload_response # Update doc info regardless
                    st.success(f"✅ File '{upload_response['filename']}' processed!")

                    if is_new_file:
                        # Inform user context is updated, DO NOT clear history/conv_id
                        st.info(f"Document context updated to '{upload_response['filename']}' for the current conversation.")
                        # Add a message to the chat history indicating the change
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"*(System: Document context updated to **{upload_response['filename']}**. I will now use this document for relevant requests in our current conversation.)*"
                        })
                        st.rerun() # Rerun to show the info message and update sidebar status
                    else:
                        st.success(f"✅ File '{upload_response['filename']}' re-processed (context updated).") # Or just 'already processed'
                    # --- MODIFICATION END ---
                else:
                    st.error("File processing failed.")
                    # Optionally clear doc info on failure?
                    # st.session_state.uploaded_file_info = None

    # Display current status
    if st.session_state.uploaded_file_info:
        st.success(f"✅ Active document: '{st.session_state.uploaded_file_info['filename']}'")
    else:
        st.info("ℹ️ No document uploaded. Chat will rely solely on conversation.")

    st.sidebar.text_input("Conversation ID", st.session_state.conversation_id, disabled=True)


# --- Chat Interface ---
st.header("💬 Chat with the AI Assistant")

# Display existing messages from session state
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], dict) and "overall_storytelling_arc" in message["content"]:
             display_pitch_deck_report(message["content"])
        elif isinstance(message["content"], str):
             # Render markdown, potentially disabling HTML if needed for security
             st.markdown(message["content"], unsafe_allow_html=False)
        else:
             st.write(str(message["content"]))


# Chat input - Now always available
if prompt := st.chat_input("Start message with @FIR, @CMO, or @General (default)..."):
    # Add user message to session state display history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send message to backend and get response
    with st.spinner("Agent is thinking..."):
        # Pass current uploaded_file_info (which can be None)
        backend_response = send_chat_message_to_backend(
            prompt,
            st.session_state.conversation_id,
            st.session_state.uploaded_file_info
        )

        if backend_response:
            st.session_state.conversation_id = backend_response.get("conversation_id", st.session_state.conversation_id)
            response_content = backend_response.get("response")
            debug_info = backend_response.get("debug_info")

            with st.chat_message("assistant"):
                assistant_message_to_store = None

                if isinstance(response_content, dict): # Report
                    display_pitch_deck_report(response_content)
                    assistant_message_to_store = response_content
                elif isinstance(response_content, str): # Text message
                    st.markdown(response_content, unsafe_allow_html=False)
                    assistant_message_to_store = response_content
                else:
                     st.markdown("Sorry, I didn't get a specific response for that.")
                     assistant_message_to_store = "No specific response received."

                if assistant_message_to_store is not None:
                    st.session_state.messages.append({"role": "assistant", "content": assistant_message_to_store})

                if debug_info:
                    with st.expander("Debug Info"):
                        st.json(debug_info)
        else:
            with st.chat_message("assistant"):
                st.error("Sorry, I couldn't get a response from the agent.")
            st.session_state.messages.append({"role": "assistant", "content": "Error: Could not connect to agent."})

    # Streamlit reruns automatically after chat input finishes