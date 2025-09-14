import streamlit as st
import io
import base64
from typing import Optional

def create_audio_recorder(key: str = "audio_recorder") -> Optional[bytes]:
    """
    Creates a custom audio recorder using HTML5 MediaRecorder API
    Returns audio bytes when recording is complete
    """
    
    # Initialize session state for this recorder
    if f"{key}_recording" not in st.session_state:
        st.session_state[f"{key}_recording"] = False
    if f"{key}_audio_data" not in st.session_state:
        st.session_state[f"{key}_audio_data"] = None
    
    # Audio recorder HTML/JavaScript component
    audio_recorder_html = f"""
    <div style="padding: 20px; border: 2px dashed #ccc; border-radius: 10px; text-align: center; background: #f9f9f9;">
        <h4>Audio Recorder</h4>
        
        <div style="margin: 15px 0;">
            <button id="start-btn-{key}" onclick="startRecording_{key}()" 
                    style="background: #4CAF50; color: white; border: none; padding: 10px 20px; margin: 5px; border-radius: 5px; cursor: pointer;">
                🎤 Start Recording
            </button>
            
            <button id="pause-btn-{key}" onclick="pauseRecording_{key}()" disabled
                    style="background: #ff9800; color: white; border: none; padding: 10px 20px; margin: 5px; border-radius: 5px; cursor: pointer;">
                ⏸️ Pause
            </button>
            
            <button id="stop-btn-{key}" onclick="stopRecording_{key}()" disabled
                    style="background: #f44336; color: white; border: none; padding: 10px 20px; margin: 5px; border-radius: 5px; cursor: pointer;">
                ⏹️ Stop
            </button>
        </div>
        
        <div id="status-{key}" style="margin: 10px 0; font-weight: bold;">Ready to record</div>
        <div id="timer-{key}" style="margin: 10px 0; font-size: 18px; color: #333;">00:00</div>
        
        <audio id="audio-playback-{key}" controls style="width: 100%; margin-top: 15px; display: none;"></audio>
        
        <div style="margin-top: 15px;">
            <button id="send-btn-{key}" onclick="sendAudio_{key}()" disabled
                    style="background: #2196F3; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; font-size: 16px;">
                📤 Send for Processing
            </button>
        </div>
    </div>

    <script>
    let mediaRecorder_{key};
    let audioChunks_{key} = [];
    let startTime_{key};
    let timerInterval_{key};
    let isPaused_{key} = false;
    
    function updateTimer_{key}() {{
        if (!isPaused_{key}) {{
            const elapsed = Date.now() - startTime_{key};
            const minutes = Math.floor(elapsed / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            document.getElementById('timer-{key}').textContent = 
                String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
        }}
    }}
    
    async function startRecording_{key}() {{
        try {{
            const stream = await navigator.mediaRecorder.getUserMedia({{ audio: true }});
            mediaRecorder_{key} = new MediaRecorder(stream);
            
            mediaRecorder_{key}.ondataavailable = event => {{
                audioChunks_{key}.push(event.data);
            }};
            
            mediaRecorder_{key}.onstop = () => {{
                const audioBlob = new Blob(audioChunks_{key}, {{ type: 'audio/wav' }});
                const audioUrl = URL.createObjectURL(audioBlob);
                const audioElement = document.getElementById('audio-playback-{key}');
                audioElement.src = audioUrl;
                audioElement.style.display = 'block';
                
                // Convert to base64 and store
                const reader = new FileReader();
                reader.onloadend = () => {{
                    const base64Audio = reader.result.split(',')[1];
                    window.parent.postMessage({{
                        type: 'audio-recorded',
                        key: '{key}',
                        audio: base64Audio
                    }}, '*');
                }};
                reader.readAsDataURL(audioBlob);
                
                document.getElementById('send-btn-{key}').disabled = false;
            }};
            
            audioChunks_{key} = [];
            mediaRecorder_{key}.start();
            startTime_{key} = Date.now();
            isPaused_{key} = false;
            timerInterval_{key} = setInterval(updateTimer_{key}, 1000);
            
            document.getElementById('start-btn-{key}').disabled = true;
            document.getElementById('pause-btn-{key}').disabled = false;
            document.getElementById('stop-btn-{key}').disabled = false;
            document.getElementById('status-{key}').textContent = 'Recording...';
            document.getElementById('status-{key}').style.color = '#4CAF50';
            
        }} catch (err) {{
            console.error('Error starting recording:', err);
            document.getElementById('status-{key}').textContent = 'Error: Could not access microphone';
            document.getElementById('status-{key}').style.color = '#f44336';
        }}
    }}
    
    function pauseRecording_{key}() {{
        if (mediaRecorder_{key} && mediaRecorder_{key}.state === 'recording') {{
            mediaRecorder_{key}.pause();
            isPaused_{key} = true;
            document.getElementById('status-{key}').textContent = 'Paused';
            document.getElementById('status-{key}').style.color = '#ff9800';
            document.getElementById('pause-btn-{key}').textContent = '▶️ Resume';
            document.getElementById('pause-btn-{key}').onclick = resumeRecording_{key};
        }}
    }}
    
    function resumeRecording_{key}() {{
        if (mediaRecorder_{key} && mediaRecorder_{key}.state === 'paused') {{
            mediaRecorder_{key}.resume();
            isPaused_{key} = false;
            document.getElementById('status-{key}').textContent = 'Recording...';
            document.getElementById('status-{key}').style.color = '#4CAF50';
            document.getElementById('pause-btn-{key}').textContent = '⏸️ Pause';
            document.getElementById('pause-btn-{key}').onclick = pauseRecording_{key};
        }}
    }}
    
    function stopRecording_{key}() {{
        if (mediaRecorder_{key}) {{
            mediaRecorder_{key}.stop();
            clearInterval(timerInterval_{key});
            
            // Stop all audio tracks
            mediaRecorder_{key}.stream.getAudioTracks().forEach(track => track.stop());
            
            document.getElementById('start-btn-{key}').disabled = false;
            document.getElementById('pause-btn-{key}').disabled = true;
            document.getElementById('stop-btn-{key}').disabled = true;
            document.getElementById('status-{key}').textContent = 'Recording complete';
            document.getElementById('status-{key}').style.color = '#2196F3';
        }}
    }}
    
    function sendAudio_{key}() {{
        window.parent.postMessage({{
            type: 'audio-send-requested',
            key: '{key}'
        }}, '*');
    }}
    </script>
    """
    
    # Display the HTML component
    st.components.v1.html(audio_recorder_html, height=300)
    
    # Listen for messages from the HTML component
    if f"{key}_send_requested" not in st.session_state:
        st.session_state[f"{key}_send_requested"] = False
    
    return st.session_state.get(f"{key}_audio_data")

def handle_audio_message(message_data):
    """Handle audio messages from the HTML component"""
    if message_data.get('type') == 'audio-recorded':
        key = message_data.get('key')
        audio_b64 = message_data.get('audio')
        if audio_b64:
            audio_bytes = base64.b64decode(audio_b64)
            st.session_state[f"{key}_audio_data"] = audio_bytes
    
    elif message_data.get('type') == 'audio-send-requested':
        key = message_data.get('key')
        st.session_state[f"{key}_send_requested"] = True