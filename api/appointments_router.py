import os
import asyncio
from datetime import datetime
import assemblyai as aai
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse # <-- Import FileResponse
from bson import ObjectId
from pymongo.collection import Collection

from schemas import (
    AppointmentCreate, AppointmentUpdate, AppointmentInDB, UserInDB, StandardResponse,
    SimpleMessageResponse, TranscriptionResponse
)
from auth import get_current_user
from database import get_db_collections
from services.gemini_service import generate_soap_summary, generate_structured_summary
from config import settings
# --- NEW IMPORT ---
from neo4j_driver import create_appointment_node_and_link_to_user

# CRITICAL: Ensure this line exists and the variable is named 'router'
router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)

aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

@router.post("/", response_model=StandardResponse[AppointmentInDB], status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment: AppointmentCreate,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    _, _, appointment_collection = collections
    
    appointment_doc = appointment.model_dump()
    appointment_doc["user_id"] = str(current_user.id)
    
    result = appointment_collection.insert_one(appointment_doc)
    created_appointment = appointment_collection.find_one({"_id": result.inserted_id})

    # --- NEW: Add appointment to Neo4j ---
    try:
        create_appointment_node_and_link_to_user(
            email=current_user.email,
            appointment_id=str(created_appointment["_id"]),
            doctor_name=created_appointment["doctor_name"],
            specialization=created_appointment["specialization"],
            appointment_time=created_appointment["appointment_time"]
        )
    except Exception as e:
        print(f"CRITICAL: Failed to create Neo4j appointment node for user {current_user.email}. Error: {e}")
    
    return StandardResponse(data=AppointmentInDB(**created_appointment), message="Appointment created successfully.")

@router.get("/", response_model=StandardResponse[list[AppointmentInDB]])
async def get_user_appointments(
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    _, _, appointment_collection = collections
    appointments = appointment_collection.find({"user_id": str(current_user.id)}).sort("appointment_time", -1)
    appointment_list = [AppointmentInDB(**appt) for appt in appointments]
    return StandardResponse(data=appointment_list)

@router.patch("/{appointment_id}", response_model=StandardResponse[AppointmentInDB])
async def update_appointment(
    appointment_id: str,
    appointment_update: AppointmentUpdate,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    """Update appointment details"""
    _, _, appointment_collection = collections
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid appointment ID.")
    
    # Check if appointment exists and belongs to user
    existing_appointment = appointment_collection.find_one(
        {"_id": ObjectId(appointment_id), "user_id": str(current_user.id)}
    )
    if not existing_appointment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")
    
    # Prepare update data (exclude None values)
    update_data = appointment_update.model_dump(exclude_unset=True, exclude_none=True)
    
    if not update_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No update data provided.")
    
    # Update the appointment
    appointment_collection.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": update_data}
    )
    
    # Return updated appointment
    updated_appointment = appointment_collection.find_one({"_id": ObjectId(appointment_id)})
    return StandardResponse(data=AppointmentInDB(**updated_appointment), message="Appointment updated successfully.")

@router.delete("/{appointment_id}", response_model=StandardResponse[SimpleMessageResponse])
async def delete_appointment(
    appointment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    """Delete an appointment"""
    _, _, appointment_collection = collections
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid appointment ID.")
    
    # Delete appointment (only if it belongs to the user)
    result = appointment_collection.delete_one(
        {"_id": ObjectId(appointment_id), "user_id": str(current_user.id)}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")
    
    # Also delete the audio file if it exists
    try:
        audio_dir = os.path.join(settings.AUDIO_FILES_DIR, str(current_user.id), appointment_id)
        if os.path.exists(audio_dir):
            import shutil
            shutil.rmtree(audio_dir)
    except Exception as e:
        # Log the error but don't fail the deletion
        print(f"Warning: Could not delete audio files for appointment {appointment_id}: {e}")
    
    return StandardResponse(data={"message": f"Appointment deleted successfully."}, message="Appointment deleted.")

# ... (the rest of the file with the process_appointment_audio function)
@router.post("/{appointment_id}/process", response_model=StandardResponse[TranscriptionResponse])
async def process_appointment_audio(
    appointment_id: str,
    audio_file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    """Transcribes, summarizes, and structures an audio file for an appointment."""
    _, _, appointment_collection = collections
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid appointment ID.")
    appointment = appointment_collection.find_one(
        {"_id": ObjectId(appointment_id), "user_id": str(current_user.id)}
    )
    if not appointment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")

    audio_dir = os.path.join(settings.AUDIO_FILES_DIR, str(current_user.id), appointment_id)
    os.makedirs(audio_dir, exist_ok=True)
    file_path = os.path.join(audio_dir, audio_file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await audio_file.read())

    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speaker_labels=True)
        transcript = transcriber.transcribe(file_path, config)
        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, transcript.error)
        formatted_transcript = "\n".join([f"Speaker {utt.speaker}: {utt.text}" for utt in transcript.utterances])
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Failed to transcribe audio: {e}")

    soap_task = generate_soap_summary(formatted_transcript)
    structured_task = generate_structured_summary(formatted_transcript)
    
    summary, structured_summary = await asyncio.gather(soap_task, structured_task)

    update_data = {
        "transcript": formatted_transcript,
        "summary": summary,
        "structured_summary": structured_summary,
        "audio_path": file_path,
        "processed_at": datetime.now()
    }
    appointment_collection.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": update_data}
    )

    response_data = TranscriptionResponse(
        appointment_id=appointment_id,
        transcript=formatted_transcript,
        summary=summary,
        structured_summary=structured_summary
    )
    return StandardResponse(data=response_data, message="Audio processed successfully.")

@router.get("/{appointment_id}/audio", response_class=FileResponse)
async def download_appointment_audio(
    appointment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    """Serves the audio file for a specific appointment for download."""
    _, _, appointment_collection = collections
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid appointment ID.")
    
    appointment = appointment_collection.find_one(
        {"_id": ObjectId(appointment_id), "user_id": str(current_user.id)}
    )
    if not appointment or not appointment.get("audio_path"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio record not found for this appointment.")

    audio_path = appointment["audio_path"]
    if not os.path.exists(audio_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found on server.")

    return FileResponse(path=audio_path, media_type='audio/wav', filename=os.path.basename(audio_path))