import requests
import streamlit as st
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

# --- Auth Functions (Unchanged) ---
def signup_user(username, email, full_name, password):
    url = f"{BASE_URL}/auth/signup"
    payload = {"username": username, "email": email, "full_name": full_name, "password": password}
    response = requests.post(url, json=payload)
    return response.json()

def login_user(username, password):
    url = f"{BASE_URL}/auth/login"
    # OAuth2PasswordRequestForm expects 'application/x-www-form-urlencoded' data
    data = {"username": username, "password": password}
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        return response.json()
    
    # --- THIS IS THE FIX ---
    # Try to parse JSON, but if it fails, use the raw text of the response.
    try:
        # This will work for standard FastAPI errors (like 401, 404)
        message = response.json().get("detail", "Unknown error")
    except requests.exceptions.JSONDecodeError:
        # This will catch 500 errors or other non-JSON responses
        message = response.text 
    return {"status": False, "message": message}

# --- NEW: User Profile Functions ---
def get_user_profile(token):
    """Fetches the current user's full profile."""
    url = f"{BASE_URL}/users/me/profile"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def update_user_profile(token, profile_data):
    """Updates the user's profile with a PATCH request."""
    url = f"{BASE_URL}/users/me/profile"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.patch(url, json=profile_data, headers=headers)
    return response.json() if response.status_code == 200 else None

# --- Chat Functions (Updated) ---
def get_chat_sessions(token):
    url = f"{BASE_URL}/chat/history"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def get_chat_history(chat_id, token):
    url = f"{BASE_URL}/chat/history/{chat_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def post_message(prompt, chat_id, token):
    url = f"{BASE_URL}/chat/"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"prompt": prompt, "chat_id": chat_id}
    response = requests.post(url, json=payload, headers=headers)
    return response.json() if response.status_code == 200 else None

# --- NEW: Chat Management Functions ---
def rename_chat(chat_id, new_name, token):
    """Renames a chat session."""
    url = f"{BASE_URL}/chat/history/{chat_id}/rename"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"new_name": new_name}
    response = requests.patch(url, json=payload, headers=headers)
    return response.json() if response.status_code == 200 else None

def delete_chat(chat_id, token):
    """Deletes a chat session."""
    url = f"{BASE_URL}/chat/history/{chat_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def find_hospitals_from_backend(token, lat, lon):
    """Calls our backend to find nearby hospitals."""
    url = f"{BASE_URL}/hospitals/nearby"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"latitude": lat, "longitude": lon}
    
    try:
        print(f"Making API call to: {url}")
        print(f"Payload: {payload}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text[:500]}...")  # First 500 chars
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return {"status": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except requests.exceptions.Timeout:
        print("Request timed out")
        return {"status": False, "error": "Request timed out after 30 seconds"}
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {"status": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"status": False, "error": f"Unexpected error: {str(e)}"}

def test_api_connection_debug():
    """Debug function to test basic API connectivity"""
    try:
        url = f"{BASE_URL}/health"
        print(f"Testing API connection to: {url}")
        response = requests.get(url, timeout=10)
        print(f"Health check status: {response.status_code}")
        return {"status": True, "message": f"API is reachable - Status: {response.status_code}"}
    except Exception as e:
        print(f"API connection failed: {e}")
        return {"status": False, "error": f"Cannot reach API: {str(e)}"}

def find_hospitals_google_places_fallback(token, lat, lon):
    """Alternative hospital finder using a different approach"""
    # This would use Google Places API as fallback
    # For now, return a mock response for testing
    return {
        "status": True,
        "data": [
            {
                "name": "Test Hospital (Mock Data)",
                "type": "Hospital",
                "latitude": lat + 0.001,
                "longitude": lon + 0.001,
                "phone": "+1-555-0123",
                "address": "123 Test Street",
                "google_maps_url": f"https://www.google.com/maps/search/?api=1&query=hospital+near+{lat},{lon}"
            }
        ],
        "message": "Mock hospital data for testing"
    }

def get_appointments(token):
    """Fetches all appointments for the user."""
    url = f"{BASE_URL}/appointments/"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def create_appointment(token, doctor_name, specialization, reason, appointment_time: datetime):
    """Creates a new appointment."""
    url = f"{BASE_URL}/appointments/"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "doctor_name": doctor_name or None,
        "specialization": specialization or None,
        "reason": reason or None,
        "appointment_time": appointment_time.isoformat()
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def update_appointment(token, appointment_id, **kwargs):
    """Updates an appointment."""
    url = f"{BASE_URL}/appointments/{appointment_id}"
    headers = {"Authorization": f"Bearer {token}"}
    # Remove None values and format datetime if present
    payload = {}
    for key, value in kwargs.items():
        if value is not None:
            if key == "appointment_time" and hasattr(value, 'isoformat'):
                payload[key] = value.isoformat()
            else:
                payload[key] = value
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.json() if response.status_code == 200 else {"status": False, "error": response.text}

def delete_appointment(token, appointment_id):
    """Deletes an appointment."""
    url = f"{BASE_URL}/appointments/{appointment_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(url, headers=headers)
    return response.json() if response.status_code == 200 else {"status": False, "error": response.text}

def upload_and_process_audio(token, appointment_id, audio_file):
    """Uploads an audio file for transcription and summarization."""
    url = f"{BASE_URL}/appointments/{appointment_id}/process"
    headers = {"Authorization": f"Bearer {token}"}
    files = {'audio_file': (audio_file.name, audio_file, audio_file.type)}
    
    response = requests.post(url, files=files, headers=headers)
    return response.json() if response.status_code == 200 else None

def get_audio_file(token, appointment_id):
    """Downloads the audio file content from the backend."""
    url = f"{BASE_URL}/appointments/{appointment_id}/audio"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content # Return the raw bytes of the file
    return None