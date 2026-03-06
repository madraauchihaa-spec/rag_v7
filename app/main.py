# app/main.py
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Add app directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.finding_mode import finding_mode
from rag.legal_mode import legal_mode
from utils.intent_classifier import classify_intent

app = FastAPI(
    title="Compliance RAG Engine",
    version="7.0.0",
    description="AI-powered Compliance Intelligence System V7"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SiteProfile(BaseModel):
    industry_type: str | None = None
    mah_status: str | None = None
    state: str | None = None


class QueryRequest(BaseModel):
    query: str
    site_profile: SiteProfile


class FindingRequest(BaseModel):
    issue: str
    site_profile: SiteProfile


class LegalRequest(BaseModel):
    query: str
    site_profile: SiteProfile


@app.get("/health")
def health():
    return {"status": "running"}


@app.get("/")
def serve_frontend():
    return FileResponse(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    )


# Router logic moved to classify_intent utility


@app.post("/rag/finding")
def rag_finding(request: FindingRequest):
    try:
        result = finding_mode(
            issue=request.issue,
            site_profile=request.site_profile.dict()
        )
        result["mode_used"] = "Finding Analysis Mode"
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/legal")
def rag_legal(request: LegalRequest):
    try:
        result = legal_mode(
            query=request.query,
            site_profile=request.site_profile.dict()
        )
        result["mode_used"] = "Legal Query Mode"
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
def unified_query(request: QueryRequest):
    try:
        intent = classify_intent(request.query)
        
        if intent == "AUDIT_FINDING":
            result = finding_mode(
                issue=request.query,
                site_profile=request.site_profile.dict()
            )
            result["mode_used"] = "Finding Analysis Mode"
        else:
            # TECHNICAL_STANDARD queries also go to legal_mode for now, as it handles Standard retrieval
            result = legal_mode(
                query=request.query,
                site_profile=request.site_profile.dict()
            )
            result["mode_used"] = "Legal Query Mode"

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    from threading import Timer
    from dotenv import load_dotenv

    load_dotenv()
    
    PORT = int(os.getenv("APP_PORT", 8001))
    SERVER_URL = f"http://127.0.0.1:{PORT}"

    def open_browser():
        # Only try to open browser if a display is available (Ubuntu desktop/GUI)
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            webbrowser.open(SERVER_URL)
        else:
            print("\nNo display detected (headless Ubuntu). Open the UI manually at:", SERVER_URL)

    print("\nStarting Compliance RAG Engine...")
    print(f"UI will be available at: {SERVER_URL}")

    # Wait 1.5 seconds for the server to start before opening browser
    Timer(1.5, open_browser).start()

    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=False)

