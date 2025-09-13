from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from pymongo.collection import Collection

# Import the new schemas
from schemas import (
    ChatRequest, ChatSession, UserInDB, ChatMessage, StandardResponse, 
    ChatTurnResponse, RenameChatRequest, SimpleMessageResponse
)
from auth import get_current_user
from database import get_db_collections
from services.gemini_service import medical_chat_service

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/", response_model=StandardResponse[ChatTurnResponse])
async def handle_chat(
    request: ChatRequest,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple[Collection, Collection] = Depends(get_db_collections)
):
    user_id = str(current_user.id)
    _, chat_collection = collections
    
    history = []
    chat_id = request.chat_id
    current_turn_number = 1

    if chat_id:
        chat_data = chat_collection.find_one(
            {"_id": ObjectId(chat_id), "user_id": user_id}
        )
        if not chat_data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found.")
        history = [ChatMessage(**msg) for msg in chat_data.get("history", [])]
        if history:
            current_turn_number = (history[-1].turn_number or 0) + 1

    ai_content, citations = await medical_chat_service.get_ai_response(
        prompt=request.prompt, 
        history=history,
        user_profile=current_user
    )

    history.append(ChatMessage(role="user", content=request.prompt, turn_number=current_turn_number))
    history.append(ChatMessage(role="assistant", content=ai_content, turn_number=current_turn_number, citations=citations))

    history_dicts = [msg.model_dump(exclude_none=True) for msg in history]
    
    # --- UPDATED LOGIC ---
    if chat_id:
        # Update existing chat and set the 'updated_at' timestamp
        chat_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"history": history_dicts, "updated_at": datetime.now(datetime.UTC)}}
        )
        final_chat_id = chat_id
    else:
        # Create new chat with a default name and timestamps
        new_chat_doc = {
            "user_id": user_id, 
            "history": history_dicts,
            "chat_name": request.prompt[:50], # Use first 50 chars of prompt as name
            "created_at": datetime.now(datetime.UTC),
            "updated_at": datetime.now(datetime.UTC)
        }
        result = chat_collection.insert_one(new_chat_doc)
        final_chat_id = str(result.inserted_id)

    response_data = ChatTurnResponse(
        chat_id=final_chat_id,
        ai_response=ai_content,
        turn_number=current_turn_number,
        citations=citations
    )
    return StandardResponse(data=response_data, message="Response generated.")

@router.get("/history", response_model=StandardResponse[List[ChatSession]])
async def get_all_chats(
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple[Collection, Collection] = Depends(get_db_collections)
):
    _, chat_collection = collections
    # --- UPDATED QUERY: Sort by 'updated_at' descending ---
    chats_cursor = chat_collection.find(
        {"user_id": str(current_user.id)}
    ).sort("updated_at", -1)
    chat_list = [ChatSession(**chat) for chat in chats_cursor]
    return StandardResponse(data=chat_list, message="Retrieved all user chats.")

@router.get("/history/{chat_id}", response_model=StandardResponse[ChatSession])
async def get_single_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple[Collection, Collection] = Depends(get_db_collections)
):
    _, chat_collection = collections
    chat_data = chat_collection.find_one(
        {"_id": ObjectId(chat_id), "user_id": str(current_user.id)}
    )
    if not chat_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return StandardResponse(data=ChatSession(**chat_data), message="Retrieved chat history.")

# --- NEW ENDPOINT: Rename Chat ---
@router.patch("/history/{chat_id}/rename", response_model=StandardResponse[RenameChatRequest])
async def rename_chat(
    chat_id: str,
    request: RenameChatRequest,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple[Collection, Collection] = Depends(get_db_collections)
):
    _, chat_collection = collections
    result = chat_collection.update_one(
        {"_id": ObjectId(chat_id), "user_id": str(current_user.id)},
        {"$set": {"chat_name": request.new_name, "updated_at": datetime.now(datetime.UTC)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found or you do not have permission to rename it.")
    
    return StandardResponse(data=request, message="Chat renamed successfully.")

# --- NEW ENDPOINT: Delete Chat ---
@router.delete("/history/{chat_id}", response_model=StandardResponse[SimpleMessageResponse])
async def delete_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple[Collection, Collection] = Depends(get_db_collections)
):
    _, chat_collection = collections
    result = chat_collection.delete_one(
        {"_id": ObjectId(chat_id), "user_id": str(current_user.id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found or you do not have permission to delete it.")
        
    return StandardResponse(data={"message": f"Chat session {chat_id} deleted successfully."})