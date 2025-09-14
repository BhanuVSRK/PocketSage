# api/user_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.collection import Collection
from bson import ObjectId

from schemas import UserProfileUpdate, UserProfile, StandardResponse, UserInDB
from auth import get_current_user
from database import get_db_collections
from neo4j_driver import update_user_node_properties

router = APIRouter(
    prefix="/users",
    tags=["User Profile"]
)

@router.get("/me/profile", response_model=StandardResponse[UserProfile])
async def get_user_profile(
    current_user: UserInDB = Depends(get_current_user)
):
    return StandardResponse(
        data=UserProfile(**current_user.model_dump()),
        message="User profile retrieved successfully."
    )

@router.patch("/me/profile", response_model=StandardResponse[UserProfile])
async def update_user_profile(
    update_data: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_user),
    collections: tuple = Depends(get_db_collections)
):
    # <-- FIX: Unpack three values
    user_collection, _, _ = collections
    update_dict = update_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided."
        )

    user_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_dict}
    )

    try:
        update_user_node_properties(email=current_user.email, properties=update_dict)
    except Exception as e:
        print(f"CRITICAL: Failed to update Neo4j node for user {current_user.email}. Error: {e}")

    updated_user_doc = user_collection.find_one({"_id": ObjectId(current_user.id)})
    
    return StandardResponse(
        data=UserProfile(**updated_user_doc),
        message="User profile updated successfully."
    )