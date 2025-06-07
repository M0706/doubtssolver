from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from env_vars import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, OPENAI_API_KEY
from services.external_request import ExternalRequest

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_ai_response(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = await ExternalRequest.send(
        url="https://openrouter.ai/api/v1/chat/completions",
        method="POST",
        headers=headers,
        json=data
    )
    if response is not None:
        response_json = response.json()
        return response_json.get("choices", [])[0].get("message", {}).get("content", "").strip()
    return "[Error: No response from AI service]" 