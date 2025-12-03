import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
from azure.core.credentials import AzureKeyCredential
import time

# ===========================
# Configuration (API Key)
# ===========================
ENDPOINT = "https://caldascheruyot-6384-resource.services.ai.azure.com/api/projects/caldascheruyot-6384"
API_KEY = "84s5Fp3rpWWo6kvRKbHohzkS6SEVYaGXrJeHbnBZUITlFtCHM36EJQQJ99BJACHYHv6XJ3w3AAAAACOGB2xd"
AGENT_ID = "asst_G60gsFHCdLuQSaOb44EXyPiZ"

# ===========================
# Page Config
# ===========================
st.set_page_config(page_title="Agent560 Chat", page_icon="robot", layout="centered")
st.title("Agent560 Chat")
st.caption("Powered by your Azure AI Project • API Key authenticated")

# ===========================
# Initialize Client (cached)
# ===========================
@st.cache_resource
def get_client():
    credential = AzureKeyCredential(API_KEY)
    client = AIProjectClient(credential=credential, endpoint=ENDPOINT)
    agent = client.agents.get_agent(AGENT_ID)
    return client, agent

client, agent = get_client()

# ===========================
# Session State
# ===========================
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ===========================
# Create Thread
# ===========================
def create_thread():
    thread = client.agents.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.messages = []
    return thread.id

if not st.session_state.thread_id:
    with st.spinner("Starting new conversation..."):
        create_thread()
    st.success("Ready to chat!")

# ===========================
# Sidebar
# ===========================
with st.sidebar:
    st.header("Controls")
    if st.button("New Chat", type="primary", use_container_width=True):
        create_thread()
        st.success("New conversation started!")
        st.rerun()
    st.info(f"Thread ID: `{st.session_state.thread_id}`")

# ===========================
# Display Chat History
# ===========================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===========================
# Chat Input
# ===========================
if prompt := st.chat_input("Type your message..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to Agent
    with st.chat_message("assistant"):
        with st.spinner("Agent560 is thinking..."):
            try:
                # 1. Add message
                client.agents.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=prompt
                )

                # 2. Run agent
                run = client.agents.runs.create_and_process(
                    thread_id=st.session_state.thread_id,
                    agent_id=agent.id
                )

                # Poll until complete (just in case)
                while run.status in ["queued", "running"]:
                    time.sleep(1)
                    run = client.agents.runs.get(thread_id=st.session_state.thread_id, run_id=run.id)

                if run.status == "failed":
                    st.error(f"Run failed: {run.last_error}")
                    response = "_Sorry, I encountered an error._"
                else:
                    # 3. Get response
                    messages = client.agents.messages.list(
                        thread_id=st.session_state.thread_id,
                        order=ListSortOrder.ASCENDING
                    )
                    response = "No response"
                    for msg in messages:
                        if msg.role == "assistant" and msg.text_messages:
                            response = msg.text_messages[-1].text.value

                # Display & save assistant reply
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.messages.append({"role": "assistant", "content": "_Something went wrong._"})
