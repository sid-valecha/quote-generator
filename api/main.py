from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from engines.quote_engine import generate_quote as get_quote
import os

app = FastAPI()

# Add CORS middleware to allow frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (fine for local development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Get the web directory path
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

# Mount static files (for favicon, etc.)
app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/")
def read_root():
    """Serve the main HTML page"""
    return FileResponse(os.path.join(web_dir, "index.html"))


@app.get("/api")
def api_info():
    return {"message": "Quote Generator API"}


@app.get("/api/quote")
def generate_quote():
    quote = get_quote()
    return {"quote": quote}

