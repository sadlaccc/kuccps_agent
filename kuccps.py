import streamlit as st
import asyncio
import nest_asyncio
import threading

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# --- Import original classes (paste your original code into a module or inline) ---
from original_code import BasicVoiceAssistant, AzureKeyCredential, InteractiveBrowserCredential  # placeholder imports

# Streamlit UI
st.title("🎤 Azure VoiceLive Assistant - Streamlit Edition")
st.write("A real-time voice assistant powered by Azure VoiceLive SDK.")

# Sidebar configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("API Key (required)", type="password", help="Enter your Azure VoiceLive API key.")("API Key", type="password")
endpoint = st.sidebar.text_input("Endpoint", "wss://api.voicelive.com/v1")
model = st.sidebar.text_input("Model", "gpt-4o-realtime-preview")
voice = st.sidebar.selectbox(
    "Voice",
    ["alloy", "echo", "fable", "onyx", "nova", "shimmer", "en-US-AvaNeural", "en-US-JennyNeural", "en-US-GuyNeural"],
)
instructions = st.sidebar.text_area(
    "Instructions",
    "You are a helpful AI assistant. Respond naturally and conversationally."
)

start_button = st.button("Start Assistant")
stop_button = st.button("Stop Assistant")

# Global state
if "assistant_thread" not in st.session_state:
    st.session_state.assistant_thread = None
if "assistant_running" not in st.session_state:
    st.session_state.assistant_running = False

# Runner wrapper
def run_assistant():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        credential = AzureKeyCredential(api_key) if api_key else InteractiveBrowserCredential()
        assistant = BasicVoiceAssistant(
            endpoint=endpoint,
            credential=credential,
            model=model,
            voice=voice,
            instructions=instructions,
        )
        loop.run_until_complete(assistant.start())
    except Exception as e:
        st.error(f"Error: {e}")

# Start
if start_button and not st.session_state.assistant_running:
    if not api_key:
        st.error("Please enter your API key before starting the assistant.")
    else:
        st.session_state.assistant_running = True
        st.session_state.assistant_thread = threading.Thread(target=run_assistant, daemon=True)
        st.session_state.assistant_thread.start()
        st.success("Assistant started. Speak into your microphone.")

# Stop
if stop_button and st.session_state.assistant_running:
    st.session_state.assistant_running = False
    st.success("Assistant stopped. Reload app to restart cleanly.")
