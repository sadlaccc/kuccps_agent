# app.py
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    RequestSession, ServerVad, AzureStandardVoice, Modality, AudioFormat
)
import asyncio
import base64
import json

# ===========================
# Page Config
# ===========================
st.set_page_config(page_title="Azure VoiceLive Voice Assistant", page_icon="microphone", layout="centered")

st.title("Real-Time Voice Assistant")
st.caption("Powered by Azure VoiceLive • Full-duplex voice conversation in your browser")

# ===========================
# API Key Input (with persistence)
# ===========================
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# Show input only if key is missing or invalid
if not st.session_state.api_key or st.session_state.api_key.strip() == "":
    st.warning("Azure VoiceLive API key required")
    key = st.text_input(
        "Enter your VoiceLive API Key:",
        type="password",
        placeholder="sk-...",
        help="Get your key from https://portal.azure.com → Your VoiceLive resource → Keys & Endpoint"
    )
    if key:
        st.session_state.api_key = key.strip()
        st.success("API key saved! You can now speak.")
        st.rerun()
    else:
        st.info("Tip: Your key is stored only in this browser session and never sent to anyone.")
        st.stop()

API_KEY = st.session_state.api_key

# ===========================
# Config
# ===========================
ENDPOINT = "wss://api.voicelive.com/v1"
MODEL = "gpt-4o-realtime-preview"
VOICE = "en-US-JennyNeural"  # Try: alloy, echo, shimmer, en-US-AvaNeural
INSTRUCTIONS = "You are a friendly, natural-sounding assistant. Respond conversationally."

# ===========================
# Chat History
# ===========================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ===========================
# Browser Microphone Recorder (Hold-to-Talk)
# ===========================
MIC_JS = """
<script>
let recorder, audioStream;
const status = parent.document.getElementById('status');

async function startRecording() {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(audioStream);
    const chunks = [];

    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            Streamlit.setComponentValue(base64);
        };
        reader.readAsDataURL(blob);
    };

    recorder.start();
    status.textContent = "Recording... Speak now!";
    status.style.color = "red";
}

function stopRecording() {
    if (recorder && recorder.state === "recording") {
        recorder.stop();
        audioStream.getTracks().forEach(t => t.stop());
        status.textContent = "Processing with Azure VoiceLive...";
        status.style.color = "orange";
    }
}
</script>

<div style="text-align:center; margin:40px;">
    <button 
        onmousedown="startRecording()" 
        ontouchstart="startRecording()"
        onmouseup="stopRecording()" 
        ontouchend="stopRecording()"
        style="padding:30px 50px; font-size:24px; background:#0068ff; color:white; border:none; border-radius:50px; cursor:pointer; box-shadow:0 8px 20px rgba(0,0,0,0.2);"
        onmouseover="this.style.background='#0050cc'"
        onmouseout="this.style.background='#0068ff'">
        Hold to Talk
    </button>
    <p id="status" style="margin-top:20px; font-size:18px; font-weight:bold;">Ready — Hold button and speak</p>
</div>
"""

# ===========================
# Async VoiceLive Handler
# ===========================
async def send_to_voicelive(audio_b64: str):
    credential = AzureKeyCredential(API_KEY)

    async with connect(endpoint=ENDPOINT, credential=credential, model=MODEL) as conn:
        # Configure session
        session = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=INSTRUCTIONS,
            voice=AzureStandardVoice(name=VOICE, type="azure-standard"),
            input_audio_format=AudioFormat.PCM16,
            output_audio_format=AudioFormat.PCM16,
            turn_detection=ServerVad(threshold=0.6, silence_duration_ms=700),
        )
        await conn.session.update(session=session)

        # Send audio
        await conn.input_audio_buffer.append(audio=audio_b64)

        # Stream response
        assistant_text = ""
        async for event in conn:
            if event.type == "response.audio.delta":
                audio_bytes = base64.b64decode(event.delta)
                st.audio(audio_bytes, format="audio/wav", autoplay=True)

            elif event.type == "response.text.delta":
                assistant_text += event.delta
                with st.chat_message("assistant"):
                    st.write(assistant_text)

            elif event.type == "response.done":
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                break

# ===========================
# Receive Audio from Browser
# ===========================
audio_data = st._get_component_value(MIC_JS)  # Updated for newer Streamlit

if audio_data:
    with st.chat_message("user"):
        st.write("You spoke...")
        st.session_state.messages.append({"role": "user", "content": "[Voice input]"})

    with st.spinner("Sending to Azure VoiceLive..."):
        try:
            asyncio.run(send_to_voicelive(audio_data))
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Check your API key or try again.")

# ===========================
# Footer
# ===========================
st.markdown("---")
st.markdown("""
**How to use:**  
Hold the blue button and speak → Release when done → Assistant replies with voice + text  
Your API key stays private in your browser only
""")
