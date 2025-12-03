# app.py
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import time

# ===========================
# Page Configuration
# ===========================
st.set_page_config(
    page_title="Azure AI Agent - Caldas Cheruyot",
    page_icon="robot",
    layout="centered"
)

st.title("Azure AI Agent Chat")
st.markdown("**Agent ID:** `asst_G60gsFHCdLuQSaOb44EXyPiZ` | Powered by Azure AI Foundry")

# ===========================
# Initialize Azure Client (cached)
# ===========================
@st.cache_resource
def get_project_client():
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        credential=credential,
        endpoint="https://caldascheruyot-6384-resource.services.ai.azure.com/api/projects/caldascheruyot-6384"
    )
    agent = client.agents.get_agent("asst_G60gsFHCdLuQSaOb44EXyPiZ")
    return client, agent

client, agent = get_project_client()

# ===========================
# Session State Management
# ===========================
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ===========================
# Create New Thread
# ===========================
def create_new_thread():
    thread = client.agents.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.chat_history = []
    st.success(f"New conversation started! Thread ID: `{thread.id}`")

# Start new conversation if none exists
if st.session_state.thread_id is None:
    create_new_thread()

# ===========================
# Sidebar: Controls
# ===========================
with st.sidebar:
    st.header("Conversation")
    if st.button("New Chat", type="primary", use_container_width=True):
        create_new_thread()
        st.rerun()

    st.info(f"**Thread ID:**\n`{st.session_state.thread_id}`")
    st.caption("Connected to Azure AI Project: caldascheruyot-6384")

# ===========================
# Display Chat Messages
# ===========================
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===========================
# Chat Input
# ===========================
if prompt := st.chat_input("Ask the agent anything..."):
    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to Azure AI Agent
    with st.chat_message("assistant"):
        with st.spinner("Agent is thinking..."):
            try:
                # 1. Add message to thread
                client.agents.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=prompt
                )

                # 2. Create and run the agent
                run = client.agents.runs.create_and_process(
                    thread_id=st.session_state.thread_id,
                    agent_id=agent.id
                )

                # Optional: poll if needed (create_and_process usually waits)
                while run.status in ["queued", "running"]:
                    time.sleep(1)
                    run = client.agents.runs.get(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id
                    )

                if run.status == "failed":
                    st.error(f"Agent failed: {run.last_error}")
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": "*Sorry, something went wrong.*"}
                    )
                else:
                    # 3. Get latest messages
                    messages = client.agents.messages.list(
                        thread_id=st.session_state.thread_id,
                        order=ListSortOrder.ASCENDING
                    )

                    assistant_response = ""
                    for msg in messages:
                        if msg.role == "assistant" and msg.text_messages:
                            assistant_response = msg.text_messages[-1].text.value

                    if assistant_response:
                        st.markdown(assistant_response)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": assistant_response}
                        )
                    else:
                        st.warning("No response received.")
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": "*No response from agent.*"}
                        )

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": "*An error occurred.*"}
                )
