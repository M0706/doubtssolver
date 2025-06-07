import os
from fastapi import FastAPI
from dotenv import load_dotenv
from db import db
from users_router import router as users_router
from qa_router import router as qa_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Doubt Solver Backend (FastAPI)")

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(qa_router, prefix="/qa", tags=["qa"])

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

@app.get("/")
def root():
    return {"message": "Doubt Solver Backend (FastAPI) is running."}
