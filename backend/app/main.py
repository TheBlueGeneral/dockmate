from fastapi import FastAPI
from app.api import routes   # ⬅️ import your routes
from dotenv import load_dotenv
import os

# Load .env variables into environment
load_dotenv()

# Optional: check if AWS creds exist
aws_keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
missing_keys = [k for k in aws_keys if not os.getenv(k)]
if missing_keys:
    print(f"Warning: Missing AWS credentials in environment: {missing_keys}")

app = FastAPI(title="DockMate 🚀")

# --- CORS for local dev & CI ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Validation error handler (prettier) ---
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Invalid request"},
    )

@app.get("/")
def read_root():
    return {"message": "Hello, DockMate is alive 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

# Include the router
app.include_router(routes.router)

