import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import time

# ========================
# Page Config & Title
# ========================
st.set_page_config(page_title="Azure AI Agent Chat", page_icon="🤖", layout="centered")
st.title("🤖 Azure AI Agent Chat")
st.caption("Powered by Azure AI Foundry + Agents")

# ========================
# Initialize Azure Client (with caching)
# ========================
@st.cache_resource
def get_ai_client():
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        credential=credential,
        endpoint="https://caldascheruyot-6384-resource.services.ai.ai.azure.com/api/projects/caldascheruyot-6384"
    )
    agent = client.agents.get_agent("asst_G60gsFHCdLuQSaOb44EXyPiZ")
    return client, agent

# ========================
# Session State Initialization
# ========================
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ========================
# Create Thread (once)
# ========================
def create_thread():
    client, _ = get_ai_client()
    thread = client.agents.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.messages = []
    return thread.id

# ========================
# Send Message & Get Response
# ========================
def send_message(user_input):
    if not st.session_state.thread_id:
        st.error("Thread not created yet!")
        return

    client, agent = get_ai_client()

    # Add user message
    client.agents.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user_input
    )
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Create and process run
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            run = client.agents.runs.create_and_process(
                thread_id=st.session_state.thread_id,
                agent_id=agent.id
            )

            # Poll for completion if needed (in case create_and_process doesn't wait fully)
            while run.status in ["queued", "running"]:
                time.sleep(1)
                run = client.agents.runs.get(thread_id=st.session_state.thread_id, run_id=run.id)

            if run.status == "failed":
                st.error(f"Agent failed: {run.last_error}")
                return

            # Fetch all messages
            messages = client.agents.messages.list(
                thread_id=st.session_state.thread_id,
                order=ListSortOrder.ASCENDING
            )

            assistant_reply = ""
            for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    # Get the latest assistant message
                    latest_text = msg.text_messages[-1].text.value
                    if latest_text not in [m["content"] for m in st.session_state.messages if m["role"] == "assistant"]:
                        assistant_reply = latest_text

            if assistant_reply:
                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
                st.write(assistant_reply)
            else:
                st.warning("No response from agent.")

# ========================
# Sidebar: Start New Chat
# ========================
with st.sidebar:
    st.header("Conversation")
    if st.button("🆕 New Chat", use_container_width=True):
        create_thread()
        st.success(f"New thread created: {st.session_state.thread_id}")
        st.rerun()

    if st.session_state.thread_id:
        st.info(f"Thread ID: `{st.session_state.thread_id}`")

# ========================
# Auto-create thread on first load
# ========================
if not st.session_state.thread_id:
    with st.spinner("Creating conversation thread..."):
        create_thread()
    st.rerun()

# ========================
# Display Chat History
# ========================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# ========================
# Chat Input
# ========================
if prompt := st.chat_input("Type your message here..."):
    with st.chat_message("user"):
        st.write(prompt)
    send_message(prompt)