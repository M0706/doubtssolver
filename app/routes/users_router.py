from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import UserRegister, UserProfile
from app.core.security import create_access_token
from app.services import user_services
from app.services.user_services import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserProfile)
async def register(user: UserRegister):
    row = await user_services.create_user(user.email, user.username, user.password)
    return UserProfile(id=row["id"], email=row["email"], username=row["username"])

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await user_services.verify_user_credentials(form_data.username, form_data.password)
    token = create_access_token({"user_id": user["id"]})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    return UserProfile(
        id=current_user["user_id"], 
        email=current_user["email"], 
        username=current_user["username"]
    )

@router.put("/profile", response_model=UserProfile)
async def update_profile(update: UserRegister, current_user: dict = Depends(get_current_user)):
    row = await user_services.update_user(current_user["user_id"], update.email, update.username, update.password)
    return UserProfile(id=row["id"], email=row["email"], username=row["username"])

@router.delete("/profile")
async def delete_profile(current_user: dict = Depends(get_current_user)):
    await user_services.delete_user(current_user["user_id"])
    return {"detail": "User deleted."} 