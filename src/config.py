import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() 

CHAT_MODEL = "gemini-2.0-flash"

EMBEDDING_MODEL = "text-embedding-3-small"

# llimteml proxy
def get_chat_client() -> OpenAI:
    return OpenAI(
        api_key="REDACTED",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

def get_embedding_client() -> OpenAI:
    return OpenAI(
        api_key="REDACTED", #os.environ["OPENAI_EMBEDDING_KEY", os.environ["OPENAI_API_KEY"]],
        base_url="https://api.openai.com/v1",
    )
