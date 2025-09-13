import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000"

# --- Auth Functions (Unchanged) ---
def signup_user(username, email, full_name, password):
    url = f"{BASE_URL}/auth/signup"
    payload = {"username": username, "email": email, "full_name": full_name, "password": password}
    response = requests.post(url, json=payload)
    return response.json()

def login_user(username, password):
    url = f"{BASE_URL}/auth/login"
    data = {"username": username, "password": password}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()
    return {"status": False, "message": response.json().get("detail", "Unknown error")}

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
    response = requests.post(url, json=payload, headers=headers)
    return response.json() if response.status_code == 200 else None