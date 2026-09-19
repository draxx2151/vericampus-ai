from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router

app = FastAPI(
    title="VeriCampus AI Backend API",
    description="API for VeriCampus AI — AI-Powered Scholarship Document Verification & Workflow Automation Platform",
    version="0.1.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 router (/api/v1/auth/...)
app.include_router(api_router)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "Welcome to VeriCampus AI Backend API",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "VeriCampus AI backend is running"
    }
