-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(150) NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Doubts table
CREATE TABLE IF NOT EXISTS doubts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    full_prompt_sent TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    subject_category VARCHAR(50),
    question_type VARCHAR(50)
); 