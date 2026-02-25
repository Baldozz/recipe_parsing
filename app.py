from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from pathlib import Path
import sys

# Ensure the root of the project is in the PYTHONPATH so we can import 'src'
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.menu_builder import generate_menu

app = FastAPI(title="Ludo's Kitchen API")

# Mount the static data directory
app.mount("/data", StaticFiles(directory="data"), name="data")

# Setup CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_INDEX = Path("data/indices")

class MenuRequest(BaseModel):
    query: str

@app.post("/api/menu")
async def create_menu(request: Request, body: MenuRequest):
    base_url = str(request.base_url).rstrip('/')
    # This runs generate_menu which takes the query
    ans = generate_menu(
        body.query,
        recipe_index_dir=str(DATA_INDEX),
        menu_index_dir="data/indices_menus",
        style_guide_path="data/chef_style_guide.md",
        base_url=base_url
    )

    # Check if ans is a string (error) or a stream
    if isinstance(ans, str):
        return {"error": False, "content": ans}

    # If it's a stream, we can stream it back using StreamingResponse
    async def event_generator():
        # Iterate over the chunks from the Gemini API
        for chunk in ans:
            yield chunk.text
            # small sleep to allow async context switching if needed
            await asyncio.sleep(0.01)

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/health")
def health():
    return {"status": "ok"}
