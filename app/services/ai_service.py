from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, OPENAI_API_KEY
from app.services.external_request import ExternalRequest

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