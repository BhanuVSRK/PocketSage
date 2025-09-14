# api/chat_router.py

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from pymongo.collection import Collection

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
    collections: tuple = Depends(get_db_collections)
):
    user_id = str(current_user.id)
    # <-- FIX: Unpack three values, keeping the second one
    _, chat_collection, _ = collections
    
    # ... (rest of the function is unchanged)
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
            last_turn = history[-1].turn_number or 0
            current_turn_number = last_turn + 1

    ai_content, citations = await medical_chat_service.get_ai_response(
        prompt=request.prompt, 
        history=history,
        user_profile=current_user
    )

    history.append(ChatMessage(role="user", content=request.prompt, turn_number=current_turn_number))
    history.append(ChatMessage(role="assistant", content=ai_content, turn_number=current_turn_number, citations=citations))

    history_dicts = [msg.model_dump(exclude_none=True) for msg in history]
    
    if chat_id:
        chat_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"history": history_dicts, "updated_at": datetime.now(timezone.utc)}}
        )
        final_chat_id = chat_id
    else:
        new_chat_doc = {
            "user_id": user_id, 
            "history": history_dicts,
            "chat_name": request.prompt[:50],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
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
    collections: tuple = Depends(get_db_collections)
):
    # <-- FIX: Unpack three values
    _, chat_collection, _ = collections
    chats_cursor = chat_collection.find(
        {"user_id": str(current_user.id)}
    ).sort("updated_at", -1)
    chat_list = [ChatSession(**chat) for chat in chats_cursor]
    return StandardResponse(data=chat_list, message="Retrieved all user chats.")

@router.get("/history/{chat_id}", response_model=StandardResponse[ChatSession])
async def get_single_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    # <-- FIX: Unpack three values
    _, chat_collection, _ = collections
    chat_data = chat_collection.find_one(
        {"_id": ObjectId(chat_id), "user_id": str(current_user.id)}
    )
    if not chat_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return StandardResponse(data=ChatSession(**chat_data), message="Retrieved chat history.")

@router.patch("/history/{chat_id}/rename", response_model=StandardResponse[RenameChatRequest])
async def rename_chat(
    chat_id: str,
    request: RenameChatRequest,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    # <-- FIX: Unpack three values
    _, chat_collection, _ = collections
    result = chat_collection.update_one(
        {"_id": ObjectId(chat_id), "user_id": str(current_user.id)},
        {"$set": {"chat_name": request.new_name, "updated_at": datetime.now(timezone.utc)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found or you do not have permission to rename it.")
    
    return StandardResponse(data=request, message="Chat renamed successfully.")

@router.delete("/history/{chat_id}", response_model=StandardResponse[SimpleMessageResponse])
async def delete_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    # <-- FIX: Unpack three values
    _, chat_collection, _ = collections
    result = chat_collection.delete_one(
        {"_id": ObjectId(chat_id), "user_id": str(current_user.id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found or you do not have permission to delete it.")
        
    return StandardResponse(data={"message": f"Chat session {chat_id} deleted successfully."})