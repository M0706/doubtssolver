from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.schemas import UserRegister, UserProfile
from app.core.security import create_access_token, decode_access_token
from app.services import user_services

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserProfile:
    payload = decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = await user_services.get_user_by_id(payload["user_id"])
    return UserProfile(id=user["id"], email=user["email"], username=user["username"])

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
async def get_profile(current_user: UserProfile = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserProfile)
async def update_profile(update: UserRegister, current_user: UserProfile = Depends(get_current_user)):
    row = await user_services.update_user(current_user.id, update.email, update.username, update.password)
    return UserProfile(id=row["id"], email=row["email"], username=row["username"])

@router.delete("/profile")
async def delete_profile(current_user: UserProfile = Depends(get_current_user)):
    await user_services.delete_user(current_user.id)
    return {"detail": "User deleted."} 