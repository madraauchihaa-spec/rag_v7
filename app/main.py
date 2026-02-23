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

app = FastAPI(
    title="Compliance RAG Engine",
    version="1.0.0",
    description="AI-powered Compliance Intelligence System"
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


# ----------------------------
# ROUTING LOGIC
# ----------------------------

LEGAL_KEYWORDS = [
    "what", "when", "how", "penalty", "as per", "section", "rule",
    "mandatory", "under", "license", "renewal", "requirement",
    "provision", "safety", "health", "welfare", "obligation"
]

FINDING_KEYWORDS = [
    "found", "observed", "broken", "blocked", "missing", "not available",
    "violation", "incident", "accident", "damage", "leak", "spill", "no "
]

def is_legal_query(query: str):
    q = query.lower()
    # If it contains finding-like words, it's probably an audit finding
    if any(word in q for word in FINDING_KEYWORDS):
        return False
    # If it's short or has legal keywords, it's a legal query
    return any(word in q for word in LEGAL_KEYWORDS) or len(q.split()) < 4


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
        if is_legal_query(request.query):
            result = legal_mode(
                query=request.query,
                site_profile=request.site_profile.dict()
            )
            result["mode_used"] = "Legal Query Mode"
        else:
            result = finding_mode(
                issue=request.query,
                site_profile=request.site_profile.dict()
            )
            result["mode_used"] = "Finding Analysis Mode"

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")

    print("\nStarting Compliance RAG Engine...")
    print("UI will be available at: http://127.0.0.1:8000")
    
    # Wait 1.5 seconds for the server to start before opening browser
    Timer(1.5, open_browser).start()
    
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
