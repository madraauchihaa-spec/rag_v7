# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag.finding_mode import finding_mode
from rag.legal_mode import legal_mode

app = FastAPI(
    title="Compliance RAG Engine",
    version="1.0.0",
    description="AI-powered Compliance Intelligence System"
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


@app.post("/query")
def unified_query(request: QueryRequest):
    """
    Unified Intelligence Endpoint. 
    Maintains smart routing but included for extra flexibility.
    """
    try:
        topic = classify_query_intent(request.query)
        if topic == "LICENSE_LEGAL":
            result = legal_mode(query=request.query, site_profile=request.site_profile.dict())
            result["mode_used"] = "Legal Query Mode"
        else:
            result = finding_mode(issue=request.query, site_profile=request.site_profile.dict())
            result["mode_used"] = "Finding Analysis Mode"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
