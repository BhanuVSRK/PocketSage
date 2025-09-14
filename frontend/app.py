import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from api_client import *
from datetime import datetime, timezone
import io
import time
# --- Page Configuration ---
st.set_page_config(page_title="SageAI Medical Advisor", page_icon="🩺", layout="wide")

# --- Session State Initialization ---
if 'page' not in st.session_state:
    st.session_state.page = "login"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'token' not in st.session_state:
    st.session_state.token = ""
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {}
if 'chat_id' not in st.session_state:
    st.session_state.chat_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'is_new_user' not in st.session_state:
    st.session_state.is_new_user = False
if 'location' not in st.session_state:
    st.session_state.location = None
if 'hospital_results' not in st.session_state:
    st.session_state.hospital_results = None
if 'appointment_id' not in st.session_state:
    st.session_state.appointment_id = None

# --- UI Rendering Functions (login, profile, hospitals are unchanged) ---
def render_login_page():
    # ... (This function is correct and unchanged)
    st.title("Welcome to SageAI 🩺")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                response = login_user(username, password)
                if response and response.get("status"):
                    st.session_state.logged_in = True
                    st.session_state.token = response["data"]["access_token"]
                    profile_res = get_user_profile(st.session_state.token)
                    if profile_res and profile_res.get("status"):
                        st.session_state.user_profile = profile_res["data"]
                    st.session_state.page = "chat"
                    st.rerun()
                else:
                    st.error(response.get("message", "Login failed."))
    with signup_tab:
        with st.form("signup_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            full_name = st.text_input("Full Name")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign Up"):
                signup_response = signup_user(username, email, full_name, password)
                if signup_response and signup_response.get("status"):
                    st.success("Account created! Logging you in...")
                    login_response = login_user(username, password)
                    if login_response and login_response.get("status"):
                        st.session_state.logged_in = True
                        st.session_state.token = login_response["data"]["access_token"]
                        profile_res = get_user_profile(st.session_state.token)
                        if profile_res and profile_res.get("status"):
                            st.session_state.user_profile = profile_res["data"]
                        st.session_state.page = "profile"
                        st.session_state.is_new_user = True
                        st.rerun()
                    else:
                        st.warning("Account created, but auto-login failed. Please go to the Login tab.")
                else:
                    st.error(signup_response.get("detail", "Signup failed."))

def render_profile_page():
    # ... (This function is correct and unchanged)
    st.title("👤 Your Health Profile")
    if st.session_state.is_new_user:
        st.info("Welcome! Please take a moment to fill out your profile. This is optional and can be updated later.")
    profile = st.session_state.user_profile
    with st.form("profile_form"):
        age = st.number_input("Age", min_value=0, max_value=120, value=profile.get("age"))
        gender_options = ["Male", "Female", "Other", "Prefer not to say"]
        current_gender = profile.get("gender")
        try:
            current_index = gender_options.index(current_gender)
        except ValueError:
            current_index = 0
        gender = st.selectbox("Gender", gender_options, index=current_index)
        weight = st.number_input("Weight (kg)", min_value=0.0, value=profile.get("weight_kg"))
        height = st.number_input("Height (cm)", min_value=0.0, value=profile.get("height_cm"))
        allergies_str = st.text_area("Allergies (one per line)", "\n".join(profile.get("allergies") or []))
        issues_str = st.text_area("Previous Medical Issues (one per line)", "\n".join(profile.get("previous_issues") or []))
        meds_str = st.text_area("Current Medications (one per line)", "\n".join(profile.get("current_medications") or []))
        if st.form_submit_button("Save Changes"):
            profile_data = {
                "age": age, "gender": gender, "weight_kg": weight, "height_cm": height,
                "allergies": [a.strip() for a in allergies_str.split("\n") if a.strip()],
                "previous_issues": [i.strip() for i in issues_str.split("\n") if i.strip()],
                "current_medications": [m.strip() for m in meds_str.split("\n") if m.strip()],
            }
            response = update_user_profile(st.session_state.token, profile_data)
            if response and response.get("status"):
                st.session_state.user_profile = response["data"]
                st.session_state.is_new_user = False
                st.success("Profile updated successfully!")
            else:
                st.error("Failed to update profile.")
    if st.button("⬅️ Back to Chat"):
        st.session_state.is_new_user = False
        st.session_state.page = "chat"
        st.rerun()

def render_hospitals_page():
    st.title("🏥 Find Nearby Medical Facilities")

    # Debug information section
    with st.expander("🔧 Debug Information", expanded=False):
        st.write("**Current Session State:**")
        st.write(f"- Location stored: {st.session_state.location is not None}")
        st.write(f"- Hospital results: {type(st.session_state.hospital_results)}")
        st.write(f"- Token present: {bool(st.session_state.token)}")
        
        if st.button("🧪 Test API Connection"):
            with st.spinner("Testing API connection..."):
                result = test_api_connection_debug()
                if result["status"]:
                    st.success(f"✅ {result['message']}")
                else:
                    st.error(f"❌ {result['error']}")

    st.divider()

    # --- STEP 1: Acquire and Store Location ---
    if st.session_state.location is None:
        st.info("Please use the widget below to grant location access in your browser.")
        
        # Location widget
        location_data = streamlit_geolocation()

        # Manual location input as fallback
        with st.expander("🌍 Or Enter Location Manually", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                manual_lat = st.number_input("Latitude", value=0.0, format="%.6f")
            with col2:
                manual_lon = st.number_input("Longitude", value=0.0, format="%.6f")
            
            if st.button("Use Manual Location"):
                st.session_state.location = {
                    'latitude': manual_lat,
                    'longitude': manual_lon
                }
                st.success("Manual location set!")
                st.rerun()

        # Process automatic location
        if location_data and location_data.get('latitude'):
            st.session_state.location = location_data
            st.rerun()
        elif location_data and location_data.get('error'):
            st.error(f"Location Error: {location_data['error'].get('message')}. Please check your browser's location permissions or use manual location input above.")

    # --- STEP 2: Use the Stored Location to Search ---
    else:
        lat = st.session_state.location['latitude']
        lon = st.session_state.location['longitude']
        st.success(f"📍 Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🏥 Find Hospitals (Main)", type="primary"):
                st.info("Making API call to backend...")
                with st.spinner("Searching for medical facilities..."):
                    response = find_hospitals_from_backend(st.session_state.token, lat, lon)
                    
                    # Enhanced result handling
                    if response and response.get("status"):
                        st.session_state.hospital_results = response.get("data", [])
                        st.success(f"✅ API call successful! Found {len(st.session_state.hospital_results)} facilities.")
                    else:
                        error_msg = response.get("error", "Unknown error") if response else "No response from server"
                        st.error(f"❌ API call failed: {error_msg}")
                        st.session_state.hospital_results = "error"
        
        with col2:
            if st.button("🧪 Test API Call", help="Debug button to test API connectivity"):
                st.info("Testing API call with debug logging...")
                with st.spinner("Testing API connection..."):
                    # Show the actual API call being made
                    st.code(f"""
API Endpoint: POST {BASE_URL}/hospitals/nearby
Authorization: Bearer {st.session_state.token[:20]}...
Payload: {{"latitude": {lat}, "longitude": {lon}}}
                    """)
                    
                    response = find_hospitals_from_backend(st.session_state.token, lat, lon)
                    
                    if response:
                        if response.get("status"):
                            st.success("✅ API call successful!")
                            st.json(response)
                        else:
                            st.error("❌ API call failed!")
                            st.json(response)
                    else:
                        st.error("❌ No response received!")

        with col3:
            if st.button("🌍 Use Different Location"):
                st.session_state.location = None
                st.session_state.hospital_results = None
                st.rerun()

        # Additional debugging section
        with st.expander("🔍 Advanced Debugging", expanded=False):
            st.write("**Raw API Response Debug:**")
            if st.button("Make Raw API Call"):
                import requests
                try:
                    url = f"{BASE_URL}/hospitals/nearby"
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    payload = {"latitude": lat, "longitude": lon}
                    
                    st.code(f"Making request to: {url}")
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    
                    st.write(f"**Status Code:** {response.status_code}")
                    st.write(f"**Headers:** {dict(response.headers)}")
                    st.code(response.text)
                    
                except Exception as e:
                    st.error(f"Raw API call failed: {e}")

    # --- STEP 3: Display Results ---
    if st.session_state.hospital_results is not None:
        st.divider()
        
        if st.session_state.hospital_results == "error":
            st.error("Could not retrieve data from the backend. Check the debug section above for details.")
        elif isinstance(st.session_state.hospital_results, list):
            if not st.session_state.hospital_results:
                st.warning("No medical facilities found in the immediate vicinity. Try expanding the search radius or check a different location.")
            else:
                st.subheader(f"🏥 Found {len(st.session_state.hospital_results)} facilities:")
                
                for i, place in enumerate(st.session_state.hospital_results):
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.subheader(f"{i+1}. {place['name']}")
                            st.write(f"**Type:** {place['type']}")
                            if place.get("address"):
                                st.write(f"**Address:** {place['address']}")
                            if place.get("phone"):
                                st.write(f"**Phone:** {place['phone']}")
                            st.write(f"**Coordinates:** {place['latitude']:.4f}, {place['longitude']:.4f}")
                        
                        with col2:
                            st.markdown(f"[📍 Open in Maps]({place['google_maps_url']})")
                            if place.get("phone"):
                                st.markdown(f"[📞 Call]({place['phone']})")

    # Back button
    if st.button("⬅️ Back to Chat"):
        st.session_state.page = "chat"
        st.session_state.hospital_results = None
        st.session_state.location = None
        st.rerun()

def render_appointments_page():
    st.title("🗓️ My Appointments")
    
    # Create new appointment section
    with st.expander("📅 Schedule a New Appointment", expanded=True):
        with st.form("new_appointment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                doctor_name = st.text_input("Doctor's Name (Optional)", placeholder="e.g., Dr. Smith")
                specialization = st.text_input("Specialization (Optional)", placeholder="e.g., Cardiologist")
            
            with col2:
                appt_date = st.date_input("Appointment Date")
                appt_time = st.time_input("Appointment Time")
            
            reason = st.text_area("Reason for Appointment (Optional)", 
                                placeholder="Describe the reason for your visit...", 
                                max_chars=500)
            
            if st.form_submit_button("📅 Schedule Appointment", type="primary"):
                appointment_datetime = datetime.combine(appt_date, appt_time)
                
                response = create_appointment(
                    st.session_state.token,
                    doctor_name.strip() if doctor_name.strip() else None,
                    specialization.strip() if specialization.strip() else None,
                    reason.strip() if reason.strip() else None,
                    appointment_datetime
                )
                
                if response and response.get("status"):
                    st.success("✅ Appointment scheduled successfully!")
                    st.rerun()
                else:
                    error_detail = response.get('detail', 'Failed to schedule appointment.')
                    st.error(f"❌ Error: {error_detail}")

    st.divider()
    st.subheader("📋 Your Appointments")
    
    # Load appointments
    appointments_response = get_appointments(st.session_state.token)
    if appointments_response and appointments_response.get("status"):
        appointments = appointments_response.get("data", [])
        
        if not appointments:
            st.info("📝 No appointments scheduled. Use the form above to create one.")
        else:
            # Group appointments by status
            today = datetime.now().date()
            upcoming = []
            past = []
            
            for appt in appointments:
                appt_dt = datetime.fromisoformat(appt['appointment_time'])
                if appt_dt.date() >= today:
                    upcoming.append(appt)
                else:
                    past.append(appt)
            
            # Display upcoming appointments
            if upcoming:
                st.subheader("📅 Upcoming Appointments")
                for appt in upcoming:
                    render_appointment_card(appt, is_upcoming=True)
            
            # Display past appointments
            if past:
                st.subheader("📜 Past Appointments")
                for appt in past:
                    render_appointment_card(appt, is_upcoming=False)
    else:
        st.error("❌ Could not load appointments.")

    if st.button("⬅️ Back to Chat"):
        st.session_state.page = "chat"
        st.rerun()

def render_appointment_card(appt, is_upcoming=True):
    """Render a single appointment card with management options"""
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])
        
        with col1:
            # Main appointment info
            if appt.get('doctor_name'):
                st.subheader(f"👨‍⚕️ Dr. {appt['doctor_name']}")
            else:
                st.subheader("👨‍⚕️ Medical Appointment")
            
            if appt.get('specialization'):
                st.caption(f"🏥 {appt['specialization']}")
            
            if appt.get('reason'):
                st.write(f"**Reason:** {appt['reason']}")
            
            # Date and time
            appt_dt = datetime.fromisoformat(appt['appointment_time'])
            st.write(f"📅 **Date:** {appt_dt.strftime('%A, %B %d, %Y')}")
            st.write(f"🕐 **Time:** {appt_dt.strftime('%I:%M %p')}")
            
            # Recording status
            if appt.get('transcript'):
                st.success("✅ Recording processed")
            else:
                st.info("📝 No recording yet")
        
        with col2:
            # Action buttons
            if st.button("📋 View Records", key=f"view_{appt['_id']}"):
                st.session_state.appointment_id = appt['_id']
                st.session_state.page = "transcribe"
                st.rerun()
            
            if st.button("✏️ Edit", key=f"edit_{appt['_id']}"):
                st.session_state[f"edit_mode_{appt['_id']}"] = True
                st.rerun()
        
        with col3:
            # Delete button (with confirmation)
            if st.button("🗑️ Delete", key=f"delete_{appt['_id']}", type="secondary"):
                st.session_state[f"confirm_delete_{appt['_id']}"] = True
                st.rerun()
        
        # Edit mode
        if st.session_state.get(f"edit_mode_{appt['_id']}", False):
            st.divider()
            st.subheader("✏️ Edit Appointment")
            
            with st.form(f"edit_form_{appt['_id']}"):
                edit_col1, edit_col2 = st.columns(2)
                
                with edit_col1:
                    new_doctor_name = st.text_input("Doctor's Name", value=appt.get('doctor_name', ''))
                    new_specialization = st.text_input("Specialization", value=appt.get('specialization', ''))
                
                with edit_col2:
                    current_dt = datetime.fromisoformat(appt['appointment_time'])
                    new_date = st.date_input("Date", value=current_dt.date())
                    new_time = st.time_input("Time", value=current_dt.time())
                
                new_reason = st.text_area("Reason", value=appt.get('reason', ''), max_chars=500)
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        new_datetime = datetime.combine(new_date, new_time)
                        
                        update_data = {
                            "doctor_name": new_doctor_name.strip() if new_doctor_name.strip() else None,
                            "specialization": new_specialization.strip() if new_specialization.strip() else None,
                            "reason": new_reason.strip() if new_reason.strip() else None,
                            "appointment_time": new_datetime
                        }
                        
                        response = update_appointment(st.session_state.token, appt['_id'], **update_data)
                        
                        if response and response.get("status"):
                            st.success("✅ Appointment updated successfully!")
                            st.session_state[f"edit_mode_{appt['_id']}"] = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to update: {response.get('error', 'Unknown error')}")
                
                with col_cancel:
                    if st.form_submit_button("❌ Cancel"):
                        st.session_state[f"edit_mode_{appt['_id']}"] = False
                        st.rerun()
        
        # Delete confirmation
        if st.session_state.get(f"confirm_delete_{appt['_id']}", False):
            st.divider()
            st.warning("⚠️ Are you sure you want to delete this appointment? This action cannot be undone and will also delete any associated recordings.")
            
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("🗑️ Yes, Delete", key=f"confirm_yes_{appt['_id']}", type="primary"):
                    response = delete_appointment(st.session_state.token, appt['_id'])
                    
                    if response and response.get("status"):
                        st.success("✅ Appointment deleted successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to delete: {response.get('error', 'Unknown error')}")
            
            with col_cancel:
                if st.button("❌ Cancel", key=f"confirm_no_{appt['_id']}"):
                    st.session_state[f"confirm_delete_{appt['_id']}"] = False
                    st.rerun()

# --- NEW: Transcription Page ---
def render_transcription_page():
    st.title("🎙️ Appointment Record")
    
    # Find appointment details
    appointments_response = get_appointments(st.session_state.token)
    appointment = None
    if appointments_response and appointments_response.get("status"):
        appointments = appointments_response.get("data", [])
        for appt in appointments:
            if appt['_id'] == st.session_state.appointment_id:
                appointment = appt
                break
    
    if not appointment:
        st.error("Could not find appointment details. Please go back.")
        if st.button("⬅️ Back to Appointments"):
            st.session_state.page = "appointments"
            st.rerun()
        return

    # Display appointment info
    appt_dt = datetime.fromisoformat(appointment['appointment_time'])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if appointment.get('doctor_name'):
            st.header(f"👨‍⚕️ Dr. {appointment['doctor_name']}")
        else:
            st.header("👨‍⚕️ Medical Appointment")
        
        if appointment.get('specialization'):
            st.subheader(f"🏥 {appointment['specialization']}")
        
        st.write(f"📅 **Date:** {appt_dt.strftime('%B %d, %Y at %I:%M %p')}")
        
        if appointment.get('reason'):
            st.write(f"📝 **Reason:** {appointment['reason']}")
    
    with col2:
        # Quick actions
        if st.button("✏️ Edit Appointment"):
            st.session_state[f"edit_mode_{appointment['_id']}"] = True
            st.session_state.page = "appointments"
            st.rerun()

    st.divider()

    # Check if recording already processed
    if appointment.get("transcript"):
        st.success("✅ Recording has been processed!")
        
        # Display results in tabs
        tab1, tab2, tab3 = st.tabs(["📋 SOAP Summary", "🔍 Clinical Details", "📝 Full Transcript"])
        
        with tab1:
            st.subheader("SOAP Summary")
            st.text_area("Summary", appointment["summary"], height=300, disabled=True, key="soap_display")

        with tab2:
            if appointment.get("structured_summary"):
                st.subheader("Structured Clinical Details")
                st.json(appointment["structured_summary"], expanded=True)
            else:
                st.info("No structured clinical details available.")

        with tab3:
            st.subheader("Full Conversation Transcript")
            st.text_area("Transcript", appointment["transcript"], height=400, disabled=True, key="transcript_display")

        # Download audio section
        if appointment.get("audio_path"):
            st.divider()
            st.subheader("📥 Download Recording")
            
            col1, col2 = st.columns(2)
            with col1:
                with st.spinner("Preparing audio file..."):
                    audio_bytes = get_audio_file(st.session_state.token, appointment["_id"])
                    if audio_bytes:
                        st.download_button(
                            label="🔊 Download Audio File",
                            data=audio_bytes,
                            file_name=f"appointment_{appointment['_id']}.wav",
                            mime="audio/wav",
                            type="primary"
                        )
                    else:
                        st.error("Could not retrieve audio file.")
            
            with col2:
                st.info("💡 **Tip:** You can download the original recording for your records.")

    else:
        # No recording yet - show recording interface
        st.info("📝 No recording has been processed for this appointment yet.")
        
        # Recording options in tabs
        tab1, tab2 = st.tabs(["🎙️ Browser Recorder", "📁 Upload File"])
        
        with tab1:
            st.subheader("🎙️ Live Audio Recording")
            st.info("Use the recorder below to capture your appointment conversation in real-time.")
            
            # HTTPS setup instructions
            with st.expander("🔧 Enable HTTPS for Microphone Access", expanded=True):
                st.markdown("""
                **To use browser recording, you need HTTPS. Follow these steps:**
                
                1. **Stop your current Streamlit app** (Ctrl+C)
                
                2. **Run with HTTPS:**
                   ```bash
                   python run_https.py
                   ```
                   
                3. **Visit:** https://localhost:8501 (not http)
                
                4. **Accept security warning:** Click "Advanced" → "Proceed to localhost"
                
                5. **Allow microphone** when prompted
                
                **Alternative quick fix:**
                - Type in Chrome: `chrome://settings/content/microphone`
                - Add `http://localhost:8501` to "Allow" list
                """)
            
            # Professional HTML5 Audio Recorder
            recorder_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .recorder-container {
                        padding: 25px;
                        border: 3px solid #0066cc;
                        border-radius: 15px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        text-align: center;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        color: white;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    }
                    .recorder-title {
                        margin-bottom: 25px;
                        font-size: 28px;
                        font-weight: bold;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                    }
                    .controls {
                        margin: 25px 0;
                        display: flex;
                        justify-content: center;
                        gap: 15px;
                        flex-wrap: wrap;
                    }
                    .btn {
                        color: white;
                        border: none;
                        padding: 18px 35px;
                        border-radius: 30px;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: bold;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                        transition: all 0.3s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }
                    .btn:hover:not(:disabled) {
                        transform: translateY(-3px);
                        box-shadow: 0 8px 25px rgba(0,0,0,0.4);
                    }
                    .btn:disabled {
                        opacity: 0.5;
                        cursor: not-allowed;
                        transform: none;
                    }
                    .btn-start { 
                        background: linear-gradient(45deg, #4CAF50, #45a049);
                        animation: pulse 2s infinite;
                    }
                    .btn-pause { background: linear-gradient(45deg, #ff9800, #f57c00); }
                    .btn-stop { background: linear-gradient(45deg, #f44336, #d32f2f); }
                    .btn-process { 
                        background: linear-gradient(45deg, #2196F3, #1976D2);
                        padding: 18px 45px;
                        font-size: 18px;
                        margin-top: 15px;
                    }
                    .status {
                        font-size: 20px;
                        font-weight: bold;
                        margin: 25px 0 15px 0;
                        padding: 15px;
                        border-radius: 10px;
                        background: rgba(255,255,255,0.1);
                        backdrop-filter: blur(10px);
                    }
                    .timer {
                        font-size: 48px;
                        font-weight: bold;
                        font-family: 'Courier New', monospace;
                        margin: 20px 0;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                        background: rgba(255,255,255,0.1);
                        padding: 20px;
                        border-radius: 15px;
                        backdrop-filter: blur(10px);
                    }
                    .audio-player {
                        width: 100%;
                        margin-top: 25px;
                        border-radius: 10px;
                    }
                    .error { 
                        background: rgba(244, 67, 54, 0.2);
                        border: 2px solid #f44336;
                    }
                    .success { 
                        background: rgba(76, 175, 80, 0.2);
                        border: 2px solid #4CAF50;
                    }
                    .warning {
                        background: rgba(255, 152, 0, 0.2);
                        border: 2px solid #ff9800;
                    }
                    @keyframes pulse {
                        0% { box-shadow: 0 6px 20px rgba(76, 175, 80, 0.3); }
                        50% { box-shadow: 0 6px 20px rgba(76, 175, 80, 0.6); }
                        100% { box-shadow: 0 6px 20px rgba(76, 175, 80, 0.3); }
                    }
                </style>
            </head>
            <body>
                <div class="recorder-container">
                    <div class="recorder-title">🎤 Professional Audio Recorder</div>
                    
                    <div class="controls">
                        <button id="start-btn" class="btn btn-start" onclick="startRecording()">
                            🎤 Start Recording
                        </button>
                        <button id="pause-btn" class="btn btn-pause" onclick="togglePause()" disabled>
                            ⏸️ Pause
                        </button>
                        <button id="stop-btn" class="btn btn-stop" onclick="stopRecording()" disabled>
                            ⏹️ Stop
                        </button>
                    </div>
                    
                    <div id="status" class="status">Ready to record</div>
                    <div id="timer" class="timer">00:00</div>
                    
                    <audio id="playback" class="audio-player" controls style="display: none;"></audio>
                    
                    <div>
                        <button id="process-btn" class="btn btn-process" onclick="processAudio()" disabled>
                            🚀 Process Recording
                        </button>
                    </div>
                </div>

                <script>
                let mediaRecorder;
                let audioChunks = [];
                let startTime;
                let timerInterval;
                let isPaused = false;
                let totalPausedTime = 0;
                let pauseStartTime;
                let recordedBlob = null;
                
                function updateTimer() {
                    if (startTime && !isPaused) {
                        const elapsed = Date.now() - startTime - totalPausedTime;
                        const minutes = Math.floor(elapsed / 60000);
                        const seconds = Math.floor((elapsed % 60000) / 1000);
                        document.getElementById('timer').textContent = 
                            String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
                    }
                }
                
                async function startRecording() {
                    try {
                        console.log('Requesting microphone access...');
                        
                        const stream = await navigator.mediaDevices.getUserMedia({
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                autoGainControl: true,
                                sampleRate: 44100
                            }
                        });
                        
                        console.log('Microphone access granted!');
                        
                        mediaRecorder = new MediaRecorder(stream);
                        
                        mediaRecorder.ondataavailable = (event) => {
                            if (event.data.size > 0) {
                                audioChunks.push(event.data);
                            }
                        };
                        
                        mediaRecorder.onstop = () => {
                            recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
                            const audioUrl = URL.createObjectURL(recordedBlob);
                            const audioElement = document.getElementById('playback');
                            audioElement.src = audioUrl;
                            audioElement.style.display = 'block';
                            document.getElementById('process-btn').disabled = false;
                        };
                        
                        audioChunks = [];
                        mediaRecorder.start(1000);
                        startTime = Date.now();
                        totalPausedTime = 0;
                        isPaused = false;
                        timerInterval = setInterval(updateTimer, 100);
                        
                        updateUI('recording');
                        document.getElementById('status').textContent = '🔴 Recording in progress...';
                        document.getElementById('status').className = 'status success';
                        
                    } catch (err) {
                        console.error('Microphone access error:', err);
                        
                        let errorMessage = '';
                        let instructions = '';
                        
                        if (err.name === 'NotAllowedError') {
                            errorMessage = '❌ Microphone access denied';
                            instructions = 'Please allow microphone access and refresh the page';
                        } else if (err.name === 'NotFoundError') {
                            errorMessage = '❌ No microphone found';
                            instructions = 'Please connect a microphone and try again';
                        } else if (err.name === 'NotSupportedError') {
                            errorMessage = '❌ Browser not supported';
                            instructions = 'Try using Chrome or Firefox';
                        } else {
                            errorMessage = '❌ Microphone access failed';
                            if (window.location.protocol === 'http:') {
                                instructions = 'Use HTTPS: python run_https.py';
                            } else {
                                instructions = 'Check browser permissions';
                            }
                        }
                        
                        document.getElementById('status').textContent = errorMessage + ' - ' + instructions;
                        document.getElementById('status').className = 'status error';
                    }
                }
                
                function togglePause() {
                    if (!mediaRecorder) return;
                    
                    if (mediaRecorder.state === 'recording') {
                        mediaRecorder.pause();
                        isPaused = true;
                        pauseStartTime = Date.now();
                        document.getElementById('pause-btn').textContent = '▶️ Resume';
                        document.getElementById('status').textContent = '⏸️ Recording paused';
                        document.getElementById('status').className = 'status warning';
                    } else if (mediaRecorder.state === 'paused') {
                        mediaRecorder.resume();
                        totalPausedTime += Date.now() - pauseStartTime;
                        isPaused = false;
                        document.getElementById('pause-btn').textContent = '⏸️ Pause';
                        document.getElementById('status').textContent = '🔴 Recording resumed...';
                        document.getElementById('status').className = 'status success';
                    }
                }
                
                function stopRecording() {
                    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                        mediaRecorder.stop();
                        clearInterval(timerInterval);
                        
                        mediaRecorder.stream.getAudioTracks().forEach(track => track.stop());
                        
                        updateUI('stopped');
                        document.getElementById('status').textContent = '✅ Recording complete - Ready to process';
                        document.getElementById('status').className = 'status success';
                    }
                }
                
                function updateUI(state) {
                    const startBtn = document.getElementById('start-btn');
                    const pauseBtn = document.getElementById('pause-btn');
                    const stopBtn = document.getElementById('stop-btn');
                    
                    if (state === 'recording') {
                        startBtn.disabled = true;
                        pauseBtn.disabled = false;
                        stopBtn.disabled = false;
                    } else if (state === 'stopped') {
                        startBtn.disabled = false;
                        pauseBtn.disabled = true;
                        stopBtn.disabled = true;
                        pauseBtn.textContent = '⏸️ Pause';
                    }
                }
                
                function processAudio() {
                    if (recordedBlob) {
                        document.getElementById('status').textContent = '🔄 Converting audio for upload...';
                        document.getElementById('status').className = 'status';
                        document.getElementById('process-btn').disabled = true;
                        document.getElementById('process-btn').textContent = '🔄 Processing...';
                        
                        // Convert blob to base64 for Streamlit
                        const reader = new FileReader();
                        reader.onloadend = function() {
                            const base64data = reader.result.split(',')[1];
                            
                            // Send message to Streamlit
                            window.parent.postMessage({
                                type: 'streamlit:componentReady',
                                audioData: base64data,
                                filename: `recording_${Date.now()}.webm`,
                                mimeType: 'audio/webm'
                            }, '*');
                            
                            document.getElementById('status').textContent = '✅ Audio ready! Processing with backend...';
                            document.getElementById('status').className = 'status success';
                        };
                        reader.readAsDataURL(recordedBlob);
                    }
                }
                
                // Check protocol and show warning
                window.addEventListener('load', function() {
                    if (window.location.protocol === 'http:') {
                        document.getElementById('status').textContent = '⚠️ HTTP detected - Microphone may not work. Use HTTPS for best results.';
                        document.getElementById('status').className = 'status warning';
                    }
                });
                </script>
            </body>
            </html>
            """
            
            # Render the enhanced HTML component
            st.components.v1.html(recorder_html, height=500)
        
        with tab2:
            st.subheader("📁 Upload Audio File")
            st.info("Upload a pre-recorded conversation file for transcription and analysis.")
            
            uploaded_file = st.file_uploader(
                "Choose your recorded audio file",
                type=['wav', 'mp3', 'm4a', 'webm', 'ogg', 'aac', 'flac'],
                help="Supported formats: WAV, MP3, M4A, WebM, OGG, AAC, FLAC"
            )
            
            if uploaded_file is not None:
                # File details and processing
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**File:** {uploaded_file.name}")
                    st.write(f"**Size:** {uploaded_file.size / 1024 / 1024:.2f} MB")
                    st.write(f"**Type:** {uploaded_file.type}")
                
                with col2:
                    st.audio(uploaded_file, format=uploaded_file.type)
                
                if st.button("🚀 Process Uploaded File", type="primary", use_container_width=True):
                    with st.spinner("Processing audio file... This may take several minutes."):
                        response = upload_and_process_audio(
                            st.session_state.token,
                            st.session_state.appointment_id,
                            uploaded_file
                        )
                    
                    if response and response.get("status"):
                        st.success("Processing completed successfully!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        error_msg = response.get('detail', 'Unknown error') if response else 'No response from server'
                        st.error(f"Processing failed: {error_msg}")

        with tab2:
            st.subheader("📁 Upload Audio File")
            st.info("Upload a pre-recorded conversation file for transcription and analysis.")
            
            uploaded_file = st.file_uploader(
                "Choose an audio file",
                type=['wav', 'mp3', 'm4a', 'webm', 'ogg'],
                help="Supported formats: WAV, MP3, M4A, WebM, OGG"
            )
            
            if uploaded_file is not None:
                # Show file details
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**File name:** {uploaded_file.name}")
                    st.write(f"**File size:** {uploaded_file.size / 1024 / 1024:.2f} MB")
                    st.write(f"**File type:** {uploaded_file.type}")
                
                with col2:
                    st.audio(uploaded_file, format=uploaded_file.type)
                
                # Processing button
                if st.button("🚀 Process Uploaded File", type="primary"):
                    with st.spinner("🔄 Processing audio file... This may take several minutes depending on file size."):
                        response = upload_and_process_audio(
                            st.session_state.token,
                            st.session_state.appointment_id,
                            uploaded_file
                        )
                    
                    if response and response.get("status"):
                        st.success("✅ Processing completed successfully!")
                        st.balloons()
                        
                        # Show quick preview of results
                        with st.expander("📋 Quick Preview", expanded=True):
                            data = response.get("data", {})
                            if data.get("summary"):
                                st.write("**SOAP Summary Preview:**")
                                st.write(data["summary"][:300] + "..." if len(data["summary"]) > 300 else data["summary"])
                        
                        time.sleep(2)  # Give user time to see the success message
                        st.rerun()
                    else:
                        error_msg = response.get('detail', 'Unknown error') if response else 'No response from server'
                        st.error(f"❌ Processing failed: {error_msg}")

    # Navigation
    st.divider()
    if st.button("⬅️ Back to All Appointments"):
        st.session_state.page = "appointments"
        st.session_state.appointment_id = None
        st.rerun()

# --- UPDATED: Chat Page Sidebar ---
def render_chat_page():
    with st.sidebar:
        st.header(f"Welcome, {st.session_state.user_profile.get('full_name', '')}!")
        if st.button("💬 Main Chat"):
            st.session_state.page = "chat"
            st.rerun()
        # --- NEW BUTTON ---
        if st.button("🗓️ My Appointments"):
            st.session_state.page = "appointments"
            st.rerun()
        if st.button("🏥 Find Hospitals"):
            st.session_state.page = "hospitals"
            st.rerun()
        if st.button("👤 My Profile"):
            st.session_state.page = "profile"
            st.rerun()
        st.divider()
        # ... (rest of the sidebar is unchanged)
        if st.button("New Chat ➕"):
            st.session_state.chat_id = None
            st.session_state.messages = []
            st.rerun()
        st.subheader("Chat History")
        sessions_response = get_chat_sessions(st.session_state.token)
        if sessions_response and sessions_response.get("status"):
            for session in sessions_response["data"]:
                chat_name = session.get('chat_name') or (session["history"][0]["content"][:30] + "..." if session["history"] else "Chat")
                with st.expander(f"📜 {chat_name}"):
                    if st.button("Load Chat", key=f"load_{session['_id']}"):
                        st.session_state.chat_id = session["_id"]
                        st.session_state.messages = session["history"]
                        st.rerun()
                    new_name = st.text_input("Rename", key=f"rename_{session['_id']}", placeholder="New name...")
                    if st.button("Save Name", key=f"save_{session['_id']}"):
                        rename_chat(session["_id"], new_name, st.session_state.token)
                        st.success("Renamed!")
                        st.rerun()
                    if st.button("Delete Chat", key=f"del_{session['_id']}", type="primary"):
                        delete_chat(session["_id"], st.session_state.token)
                        if st.session_state.chat_id == session["_id"]:
                            st.session_state.chat_id = None
                            st.session_state.messages = []
                        st.rerun()
        if st.button("Logout 👋"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # ... (rest of the chat page logic is unchanged)
    st.title("SageAI Medical Advisor")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                citations_md = "Sources: " + ", ".join(f"[[{c['index']}]({c['url']})]({c['title']})" for c in msg["citations"])
                st.markdown(f"<small>{citations_md}</small>", unsafe_allow_html=True)
    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("SageAI is thinking..."):
                response = post_message(prompt, st.session_state.chat_id, st.session_state.token)
                if response and response.get("status"):
                    data = response["data"]
                    st.session_state.chat_id = data["chat_id"]
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["ai_response"],
                        "citations": data.get("citations")
                    })
                    st.rerun()
                else:
                    st.error("Failed to get a response from the AI.")

# --- Main Page Router ---
if not st.session_state.logged_in:
    render_login_page()
elif st.session_state.page == "profile":
    render_profile_page()
elif st.session_state.page == "hospitals":
    render_hospitals_page()
# --- NEW ROUTING LOGIC ---
elif st.session_state.page == "appointments":
    render_appointments_page()
elif st.session_state.page == "transcribe":
    render_transcription_page()
else: # Default to chat page
    render_chat_page()