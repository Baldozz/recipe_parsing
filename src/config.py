import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() 

CHAT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-large"  

# llimteml proxy
def get_chat_client() -> OpenAI:
    return OpenAI(
        api_key="REDACTED",
        base_url = "https://litellm.sph-prod.ethz.ch",
    )

def get_embedding_client() -> OpenAI:
    return OpenAI(
        api_key="REDACTED", #os.environ["OPENAI_EMBEDDING_KEY", os.environ["OPENAI_API_KEY"]],
        base_url="https://api.openai.com/v1",
    )
