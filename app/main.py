import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# Add the 'app' directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.finding_mode import finding_mode
from rag.legal_mode import legal_mode

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Compliance RAG Engine",
    version="1.0.0",
    description="AI-powered Compliance Intelligence System"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ----------------------------
# Shared Models
# ----------------------------

class SiteProfile(BaseModel):
    industry_type: str | None = None
    mah_status: str | None = None
    state: str | None = None

@app.get("/health")
def health():
    return {"status": "running"}

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html"))


from utils.intent_classifier import classify_query_intent

# ----------------------------
# Unified Request Model
# ----------------------------

class QueryRequest(BaseModel):
    query: str  # Can be an 'issue' or a 'legal query'
    site_profile: SiteProfile


class FindingRequest(BaseModel):
    issue: str
    site_profile: SiteProfile


class LegalRequest(BaseModel):
    query: str
    site_profile: SiteProfile


# ----------------------------
# Endpoints (Aligned with Blueprint)
# ----------------------------

@app.post("/rag/finding")
def rag_finding(request: FindingRequest):
    """
    Finding Mode: Analyzes specific audit findings against experience and law.
    """
    try:
        result = finding_mode(
            issue=request.issue,
            site_profile=request.site_profile.dict()
        )
        result["mode_used"] = "Finding Analysis Mode"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/legal")
def rag_legal(request: LegalRequest):
    """
    Legal Mode: Direct Q&A against the Factoty Acts and Rules.
    """
    try:
        result = legal_mode(
            query=request.query,
            site_profile=request.site_profile.dict()
        )
        result["mode_used"] = "Legal Query Mode"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


LEGAL_KEYWORDS = ["what", "when", "penalty", "as per", "section", "rule", "mandatory"]

def is_legal_query(query):
    query_lower = query.lower()
    return any(word in query_lower for word in LEGAL_KEYWORDS)

@app.post("/query")
def unified_query(request: QueryRequest):
    """
    Unified Intelligence Endpoint. 
    Maintains smart routing but included for extra flexibility.
    """
    try:
        topic = classify_query_intent(request.query)
        # Enhanced Routing Logic
        if topic == "LICENSE_LEGAL" or is_legal_query(request.query):
            result = legal_mode(query=request.query, site_profile=request.site_profile.dict())
            result["mode_used"] = "Legal Query Mode"
        else:
            result = finding_mode(issue=request.query, site_profile=request.site_profile.dict())
            result["mode_used"] = "Finding Analysis Mode"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
