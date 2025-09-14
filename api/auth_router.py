# api/auth_router.py

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.collection import Collection

from schemas import UserCreate, UserBase, Token, StandardResponse
from auth import hash_password, verify_password, create_access_token
from database import get_db_collections
from neo4j_driver import create_user_node

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/signup", response_model=StandardResponse[UserBase], status_code=status.HTTP_201_CREATED)
async def signup(
    user: UserCreate,
    collections: tuple = Depends(get_db_collections) # Changed for clarity
):
    # <-- FIX: Unpack three values, ignoring the last two
    user_collection, _, _ = collections    
    
    if user_collection.find_one({"$or": [{"email": user.email}, {"username": user.username}]}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )
    
    hashed_pass = hash_password(user.password)
    user_data = user.model_dump()
    user_data["hashed_password"] = hashed_pass
    del user_data["password"]
    
    user_collection.insert_one(user_data)
    
    try:
        create_user_node(email=user.email, full_name=user.full_name, username=user.username)
    except Exception as e:
        print(f"CRITICAL: Failed to create Neo4j node for user {user.email}. Error: {e}")

    return StandardResponse(data=user, message="User created successfully.")

@router.post("/login", response_model=StandardResponse[Token])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    collections: tuple = Depends(get_db_collections) # Changed for clarity
):
    # <-- FIX: Unpack three values, ignoring the last two
    user_collection, _, _ = collections
    
    user = user_collection.find_one({"$or": [{"email": form_data.username}, {"username": form_data.username}]})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    token_data = Token(access_token=access_token, token_type="bearer")
    return StandardResponse(data=token_data, message="Login successful.")