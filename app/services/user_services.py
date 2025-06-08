import asyncpg
from app.core.db import db
from app.core.security import hash_password, verify_password
from fastapi import HTTPException

async def create_user(email: str, username: str, password: str):
    pool = await db.get_pool()
    existing = await pool.fetchrow("SELECT id FROM users WHERE email = $1", email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(password)
    row = await pool.fetchrow(
        """
        INSERT INTO users (email, username, password) VALUES ($1, $2, $3)
        RETURNING id, email, username
        """, email, username, hashed
    )
    if not row:
        raise HTTPException(status_code=500, detail="User creation failed")
    return row

async def get_user_by_email(email: str):
    pool = await db.get_pool()
    user = await pool.fetchrow("SELECT id, email, username, password FROM users WHERE email = $1", email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_user_by_id(user_id: int):
    pool = await db.get_pool()
    user = await pool.fetchrow("SELECT id, email, username FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def update_user(user_id: int, email: str, username: str, password: str):
    pool = await db.get_pool()
    hashed = hash_password(password)
    row = await pool.fetchrow(
        """
        UPDATE users SET email = $1, username = $2, password = $3 WHERE id = $4
        RETURNING id, email, username
        """, email, username, hashed, user_id
    )
    if not row:
        raise HTTPException(status_code=500, detail="User update failed")
    return row

async def delete_user(user_id: int):
    pool = await db.get_pool()
    result = await pool.execute("DELETE FROM users WHERE id = $1", user_id)
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="User not found or already deleted")
    return True

async def verify_user_credentials(email: str, password: str):
    pool = await db.get_pool()
    user = await pool.fetchrow("SELECT id, email, username, password FROM users WHERE email = $1", email)
    print(user)
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return user 