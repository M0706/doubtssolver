from fastapi import APIRouter, Depends, HTTPException
from app.schemas import DoubtEntryCreate, DoubtEntryOut, UserProfile
from app.services.ai_service import get_ai_response
from app.routes.users_router import get_current_user
from app.services import qa_services

router = APIRouter()

@router.post("/ask", response_model=DoubtEntryOut)
async def ask_question(doubt: DoubtEntryCreate, current_user: UserProfile = Depends(get_current_user)):
    # Prompt engineering
    prompt = (
        "You are an expert GMAT tutor. Your goal is to help GMAT students solve problems and understand concepts clearly and concisely.\n"
    )
    if doubt.question_type:
        prompt += f"Question Type: {doubt.question_type}\n"
    prompt += f"Student's Question: {doubt.question_text}\n"
    if doubt.options:
        options_str = "\n".join([f"{k}. {v}" for k, v in doubt.options.items()])
        prompt += f"Options:\n{options_str}\n"
    prompt += "Please provide a clear and concise answer, explaining your reasoning."

    try:
        ai_response = await get_ai_response(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    row = await qa_services.create_doubt_entry(
        user_id=current_user.id,
        question_text=doubt.question_text,
        full_prompt_sent=prompt,
        ai_response=ai_response,
        subject_category=doubt.subject_category
    )
    return DoubtEntryOut(**dict(row)) 