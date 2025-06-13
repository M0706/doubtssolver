from fastapi import APIRouter, Depends, HTTPException
from app.schemas import DoubtEntryCreate, DoubtEntryOut, UserProfile
from app.services.ai_service import get_ai_response
from app.routes.users_router import get_current_user
from app.services import qa_services
from app.utils.prompt_engineering import generate_gmat_prompt

router = APIRouter()

@router.post("/ask", response_model=DoubtEntryOut)
async def ask_question(doubt: DoubtEntryCreate, current_user: UserProfile = Depends(get_current_user)):
    # Prompt engineering
    try:
        system_prompt, user_prompt, final_subject, final_qtype = await generate_gmat_prompt(doubt)
        full_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}"
        ai_response = await get_ai_response(full_prompt)
        print(f"AI Response: {ai_response}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    try:
        row = await qa_services.create_doubt_entry(
            user_id=current_user.id,
            question_text=doubt.question_text,
            full_prompt_sent=full_prompt,
            ai_response=ai_response,
            subject_category=final_subject,
            question_type=final_qtype
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return DoubtEntryOut(**dict(row))
