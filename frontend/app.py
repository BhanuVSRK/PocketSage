import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from api_client import *
from st_audiorec import st_audiorec
from datetime import datetime, timezone
import io   
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

    # --- STEP 1: Acquire and Persist Location ---
    if st.session_state.location is None:
        st.info("Please use the widget below to grant location access.")
        # This widget's only job is to get the location and trigger a rerun
        location_data = streamlit_geolocation()

        if location_data and location_data.get('latitude'):
            # As soon as we get data, save it to the persistent state and rerun
            st.session_state.location = location_data
            st.rerun()
        elif location_data and location_data.get('error'):
            st.error(f"Location Error: {location_data['error'].get('message')}. Please check browser permissions.")

    # --- STEP 2: Use the Persisted Location to Search ---
    else:
        lat = st.session_state.location['latitude']
        lon = st.session_state.location['longitude']
        st.success(f"Location acquired: Latitude {lat:.4f}, Longitude {lon:.4f}")

        if st.button("Find Facilities Near Me", type="primary"):
            with st.spinner("Calling backend to find facilities..."):
                response = find_hospitals_from_backend(st.session_state.token, lat, lon)
                if response and response.get("status"):
                    st.session_state.hospital_results = response.get("data", [])
                else:
                    st.session_state.hospital_results = "error"
        
        if st.button("Use a Different Location"):
            st.session_state.location = None
            st.session_state.hospital_results = None
            st.rerun()

    # --- STEP 3: Display Results (reads from session state) ---
    if st.session_state.hospital_results == "error":
        st.error("Could not retrieve data from the backend. Please try again.")
    elif isinstance(st.session_state.hospital_results, list):
        if not st.session_state.hospital_results:
            st.warning("No medical facilities were found in the immediate vicinity.")
        else:
            st.subheader(f"Found {len(st.session_state.hospital_results)} facilities near you:")
            for place in st.session_state.hospital_results:
                with st.container(border=True):
                    st.subheader(place["name"])
                    st.write(f"**Type:** {place['type']}")
                    if place.get("address"):
                        st.write(f"**Address:** {place['address']}")
                    st.markdown(f"[Open in Google Maps]({place['google_maps_url']})")
                    if place.get("phone"):
                        st.markdown(f"[Call ({place['phone']})](tel:{place['phone']})")

    if st.button("⬅️ Back to Chat"):
        st.session_state.page = "chat"
        st.session_state.hospital_results = None
        st.session_state.location = None
        st.rerun()



def render_appointments_page():
    st.title("🗓️ My Appointments")
    
    with st.expander("Schedule a New Appointment", expanded=True): # Expanded for easier testing
        with st.form("new_appointment_form"):
            doctor_name = st.text_input("Doctor's Name")
            specialization = st.text_input("Specialization (e.g., Cardiologist)")
            appt_date = st.date_input("Appointment Date")
            appt_time = st.time_input("Appointment Time")
            
            if st.form_submit_button("Schedule Appointment"):
                if doctor_name and specialization:
                    # --- THIS IS THE FIX ---
                    # 1. Combine the date and time from Streamlit's widgets
                    appointment_datetime = datetime.combine(appt_date, appt_time)
                    
                    # 2. Call the API client with the correct datetime object
                    response = create_appointment(
                        st.session_state.token,
                        doctor_name,
                        specialization,
                        appointment_datetime
                    )
                    if response and response.get("status"):
                        st.success("Appointment scheduled successfully!")
                        st.rerun() # Rerun to refresh the appointment list
                    else:
                        # Display a more detailed error if available
                        error_detail = response.get('detail', 'Failed to schedule appointment.')
                        st.error(f"Error: {error_detail}")
                else:
                    st.warning("Please fill in all fields.")

    st.divider()
    st.subheader("Upcoming & Past Appointments")
    
    appointments_response = get_appointments(st.session_state.token)
    if appointments_response and appointments_response.get("status"):
        appointments = appointments_response.get("data", [])
        if not appointments:
            # --- FIX: More user-friendly message ---
            st.info("You have no scheduled appointments. Use the form above to create one.")
        else:
            for appt in appointments:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.subheader(f"Dr. {appt['doctor_name']}")
                        st.caption(appt['specialization'])
                    with col2:
                        # Pydantic/FastAPI returns ISO format string, so we parse it
                        appt_dt = datetime.fromisoformat(appt['appointment_time'])
                        st.write(f"**Date:** {appt_dt.strftime('%A, %B %d, %Y')}")
                        st.write(f"**Time:** {appt_dt.strftime('%I:%M %p')}")
                    with col3:
                        if st.button("View Records", key=f"view_{appt['_id']}"):
                            st.session_state.appointment_id = appt['_id']
                            st.session_state.page = "transcribe"
                            st.rerun()
    else:
        st.error("Could not load appointments.")

    if st.button("⬅️ Back to Chat"):
        st.session_state.page = "chat"
        st.rerun()

# --- NEW: Transcription Page ---
def render_transcription_page():
    st.title("🎙️ Appointment Record")
    
    # ... (code to find the appointment is unchanged)
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

    appt_dt = datetime.fromisoformat(appointment['appointment_time'])
    st.header(f"Dr. {appointment['doctor_name']} ({appointment['specialization']})")
    st.subheader(appt_dt.strftime('%B %d, %Y at %I:%M %p'))
    st.divider()

    if appointment.get("transcript"):
        st.subheader("SOAP Summary")
        st.text_area("Summary", appointment["summary"], height=200, disabled=True)

        if appointment.get("structured_summary"):
            st.subheader("Structured Clinical Details")
            st.json(appointment["structured_summary"], expanded=True)

        st.subheader("Full Conversation Transcript")
        st.text_area("Transcript", appointment["transcript"], height=300, disabled=True)

        # --- NEW: Download Button ---
        if appointment.get("audio_path"):
            st.subheader("Download Recording")
            with st.spinner("Preparing audio for download..."):
                audio_bytes = get_audio_file(st.session_state.token, appointment["_id"])
                if audio_bytes:
                    st.download_button(
                        label="Download Audio File",
                        data=audio_bytes,
                        file_name=f"appointment_{appointment['_id']}.wav",
                        mime="audio/wav"
                    )
                else:
                    st.error("Could not retrieve audio file.")

    else:
        st.info("No record has been processed for this appointment yet. You can record audio or upload a file below.")

        # --- NEW: Live Audio Recorder ---
        st.subheader("Record Audio")
        audio_bytes = st_audiorec()
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            if st.button("Process Recorded Audio", type="primary"):
                # Convert bytes to a file-like object for the API
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = f"recording_{st.session_state.appointment_id}.wav" # Give it a name
                
                with st.spinner("Uploading and processing recording... This may take a few minutes."):
                    response = upload_and_process_audio(
                        st.session_state.token,
                        st.session_state.appointment_id,
                        audio_file
                    )
                if response and response.get("status"):
                    st.success("Processing complete!")
                    st.rerun()
                else:
                    st.error(f"An error occurred: {response.get('detail', 'Unknown error')}")

        st.divider()
        st.subheader("Or Upload an Audio File")
        uploaded_file = st.file_uploader(
            "Upload a conversation recording (WAV, MP3, M4A)",
            type=['wav', 'mp3', 'm4a']
        )
        if uploaded_file is not None:
            if st.button("Process Uploaded File"):
                with st.spinner("Uploading and processing file... This may take a few minutes."):
                    response = upload_and_process_audio(
                        st.session_state.token,
                        st.session_state.appointment_id,
                        uploaded_file
                    )
                if response and response.get("status"):
                    st.success("Processing complete!")
                    st.rerun()
                else:
                    st.error(f"An error occurred: {response.get('detail', 'Unknown error')}")

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