import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() 

# CHAT_MODEL = "gemini-2.5-pro"
CHAT_MODEL = "gemini-2.0-flash"
EMBEDDING_MODEL = "text-embedding-004"

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"

def get_chat_client() -> OpenAI:
    return OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url=_GEMINI_BASE)

def get_embedding_client() -> OpenAI:
    return OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url=_GEMINI_BASE)
