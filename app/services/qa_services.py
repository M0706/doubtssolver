from app.core.db import db
from fastapi import HTTPException
from datetime import datetime

async def create_doubt_entry(user_id: int, question_text: str, full_prompt_sent: str, ai_response: str, subject_category: str = None):
    pool = await db.get_pool()
    now = datetime.utcnow()
    row = await pool.fetchrow(
        """
        INSERT INTO doubts (user_id, question_text, full_prompt_sent, ai_response, timestamp, subject_category)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, user_id, question_text, full_prompt_sent, ai_response, timestamp, subject_category
        """,
        user_id, question_text, full_prompt_sent, ai_response, now, subject_category
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create doubt entry")
    return row 