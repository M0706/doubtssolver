import os
from dotenv import load_dotenv

# Explicitly load environment variables from resources/doubtsolver.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'doubtsolver.env'))

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = os.environ["JWT_ALGORITHM"]
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ["ACCESS_TOKEN_EXPIRE_HOURS"])
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
DATABASE_URL = os.environ.get("DATABASE_URL") 