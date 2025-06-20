# Doubt Solver Backend (FastAPI Version)

A reimplementation of the original Django-based doubt-solving backend using FastAPI, Pydantic, and custom SQL queries (no ORM). This version is designed for transparency, performance, and explicit control over all logic.

## Stack
- FastAPI (web framework)
- Pydantic (data validation)
- asyncpg (PostgreSQL async driver)
- python-jose (JWT handling)
- passlib (password hashing)
- httpx (async HTTP for OpenAI API)

## Features
- User registration, login, and profile APIs (JWT-based)
- Submit a question and get an AI-generated answer (OpenAI GPT-3.5-turbo)
- PostgreSQL database support (custom SQL, no ORM)
- Extensible for multiple subjects

## Setup Instructions

1. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure environment variables:**
    - Create a `.env` file in this directory with:
      ```env
      DEBUG=True
      SECRET_KEY=your-secret-key
      OPENAI_API_KEY=your-openai-api-key
      DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
      JWT_ALGORITHM=HS256
      ACCESS_TOKEN_EXPIRE_HOURS=24
      ```

4. **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```

5. **API Endpoints:**
    - `POST /users/register` — Register a new user
    - `POST /users/login` — Login and get JWT token
    - `GET /users/profile` — Get user profile (auth required)
    - `POST /qa/ask` — Submit a question (auth required)

## Notes
- All database operations use custom SQL queries for full transparency.
- JWT authentication is handled with python-jose.
- See code for further extensibility. 
