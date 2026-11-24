"""
FastAPI Enterprise Production Application
ClauseVerify AI - Multi-Tenant Legal & Compliance Platform
With Workspace Isolation, Persistent SQLite Storage, and Swagger Docs
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

import database
from database import get_connection
import integrations

# Initialize FastAPI App
app = FastAPI(
    title="ClauseVerify AI — Enterprise API",
    description="Zero-Hallucination Contract Intelligence & Compliance Platform with Multi-Tenant Workspace Isolation.",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# -------------------------------------------------------------
# Pydantic Request & Response Models
# -------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    document_id: str

class UploadRequest(BaseModel):
    title: str
    content: str
    doc_type: Optional[str] = "Custom Agreement"

class QuestionnaireRequest(BaseModel):
    document_id: str
    questions: List[str]

class SwitchUserRequest(BaseModel):
    email: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    company_name: str
    role: Optional[str] = "Compliance Officer"

# -------------------------------------------------------------
# Multi-Tenant Authentication & Session Dependency
# -------------------------------------------------------------
def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    token = None
    if authorization:
        token = authorization.replace("Bearer ", "").strip()

    user = None
    if token:
        cursor.execute("SELECT u.*, w.name as workspace_name, w.domain as workspace_domain, w.plan as workspace_plan FROM users u JOIN workspaces w ON u.workspace_id = w.id WHERE u.auth_token = ?", (token,))
        user = cursor.fetchone()

    # Default fallback to Sarah Chen (Acme Global) if no token provided
    if not user:
        cursor.execute("SELECT u.*, w.name as workspace_name, w.domain as workspace_domain, w.plan as workspace_plan FROM users u JOIN workspaces w ON u.workspace_id = w.id WHERE u.email = 'sarah.chen@acme.com'")
        user = cursor.fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authentication Token")

    return dict(user)

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.get("/api/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns current authenticated user and isolated workspace profile."""
    plan = (current_user.get("workspace_plan") or "growth").lower()
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "auth_token": current_user["auth_token"],
        "workspace": {
            "id": current_user["workspace_id"],
            "name": current_user["workspace_name"],
            "domain": current_user["workspace_domain"],
            "plan": plan
        }
    }

@app.post("/api/auth/switch-user")
async def switch_user(req: SwitchUserRequest):
    """Switch active user persona / login."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT u.*, w.name as workspace_name, w.domain as workspace_domain FROM users u JOIN workspaces w ON u.workspace_id = w.id WHERE u.email = ?", (req.email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    user_dict = dict(user)
    return {
        "status": "success",
        "auth_token": user_dict["auth_token"],
        "user": user_dict
    }

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    """Registers a new user and creates an isolated enterprise workspace."""
    res = database.register_user(req.email, req.password, req.full_name, req.company_name, req.role)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Authenticates user with email and password."""
    res = database.login_user(req.email, req.password)
    if "error" in res:
        raise HTTPException(status_code=401, detail=res["error"])
    return res

@app.get("/api/documents")
async def list_documents(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Strict Multi-Tenant Document Listing: Only returns contracts belonging to user's workspace."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, title, doc_type as type, effective_date, parties, pages_json 
    FROM documents 
    WHERE workspace_id = ?
    ORDER BY created_at DESC
    """, (current_user["workspace_id"],))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        pages = json.loads(r["pages_json"])
        results.append({
            "id": r["id"],
            "title": r["title"],
            "type": r["type"],
            "effective_date": r["effective_date"],
            "parties": r["parties"],
            "page_count": len(pages)
        })
    return results

@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Fetch contract details ensuring tenant access control."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ? AND workspace_id = ?", (doc_id, current_user["workspace_id"]))
    doc = cursor.fetchone()
    conn.close()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")

    doc_dict = dict(doc)
    doc_dict["pages"] = json.loads(doc_dict["pages_json"])
    del doc_dict["pages_json"]
    return doc_dict

@app.post("/api/upload")
async def upload_document(req: UploadRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Persistent Document Ingestion: Saves to SQLite permanently under active workspace."""
    from server import parse_raw_text_into_document
    parsed = parse_raw_text_into_document(req.title, req.content, req.doc_type)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO documents (id, workspace_id, title, doc_type, effective_date, parties, pages_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        parsed["id"],
        current_user["workspace_id"],
        parsed["title"],
        parsed["type"],
        parsed["effective_date"],
        f"Uploaded by {current_user['full_name']}",
        json.dumps(parsed["pages"]),
        datetime.utcnow().isoformat() + "Z"
    ))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "document": {
            "id": parsed["id"],
            "title": parsed["title"],
            "page_count": len(parsed["pages"]),
            "workspace_id": current_user["workspace_id"]
        }
    }

@app.post("/api/query")
async def execute_query(req: QueryRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Executes verified query, checks for contract amendment drift, and logs to audit ledger."""
    from server import search_and_verify
    res = search_and_verify(req.query, req.document_id, current_user["full_name"])

    # Check for Contract Family Amendment Drift
    if res.get("citations") and len(res["citations"]) > 0:
        top_title = res["citations"][0].get("title", "")
        amend_warning = integrations.check_amendment_drift(req.document_id, top_title)
        if amend_warning:
            res["amendment_warning"] = amend_warning
            res["answer"] = (
                f"⚠️ **AMENDMENT ALERT ({amend_warning['effective_date']}):**\n"
                f"This clause was **modified and superseded** by **{amend_warning['title']}**:\n"
                f"> \"{amend_warning['superseded_text']}\"\n\n"
                f"**Original Clause Record:**\n"
                f"{res['answer']}"
            )

    # Update audit record with workspace_id
    if res.get("audit_id"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE audit_logs SET workspace_id = ? WHERE id = ?", (current_user["workspace_id"], res["audit_id"]))
        conn.commit()
        conn.close()

    return res

# -------------------------------------------------------------
# Enterprise Cloud Connectors & Workflow Integrations
# -------------------------------------------------------------
@app.get("/api/integrations/cloud-drives")
async def get_cloud_drives(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Lists available cloud storage drives and folders for one-click ingestion."""
    return integrations.MOCK_CLOUD_DRIVES

class CloudSyncRequest(BaseModel):
    provider: str
    folder_index: int = 0

@app.post("/api/integrations/cloud-sync")
async def sync_cloud_files(req: CloudSyncRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Syncs a folder from Google Drive or SharePoint into the workspace."""
    workspace_plan = (current_user.get("workspace_plan") or "growth").lower()
    if workspace_plan == "starter":
        raise HTTPException(
            status_code=403,
            detail="⚡ Plan Gated: Cloud Drive Sync (Google Drive & SharePoint) requires a Growth ($799/mo) or Enterprise plan. Please upgrade in the Pricing menu."
        )
    files = integrations.sync_cloud_folder(req.provider, req.folder_index)
    if not files:
        raise HTTPException(status_code=400, detail="Cloud folder empty or invalid provider")

    # Ingest synced contracts into database
    conn = get_connection()
    cursor = conn.cursor()
    ingested = []
    from server import parse_raw_text_into_document
    now = datetime.utcnow().isoformat() + "Z"

    for f in files:
        sample_body = (
            f"CLOUDDOC: {f['name']}\n"
            f"This contract was synced from enterprise {req.provider.upper()}.\n\n"
            f"Section 1. Cloud Storage Terms\n"
            f"Enterprise cloud terms apply to all transactions processed hereunder.\n\n"
            f"Section 2. Audit and Security\n"
            f"Security compliance certified under ISO/IEC 27001 and SOC 2 guidelines."
        )
        parsed = parse_raw_text_into_document(f["name"].replace(".pdf", "").replace("_", " "), sample_body, f["type"])
        cursor.execute("""
        INSERT INTO documents (id, workspace_id, title, doc_type, effective_date, parties, pages_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            parsed["id"],
            current_user["workspace_id"],
            parsed["title"],
            parsed["type"],
            parsed["effective_date"],
            f"Synced from {req.provider}",
            json.dumps(parsed["pages"]),
            now
        ))
        ingested.append({"id": parsed["id"], "name": f["name"]})

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "provider": req.provider,
        "synced_count": len(ingested),
        "files": ingested
    }

class SlackCommandRequest(BaseModel):
    command: str
    text: str
    document_id: Optional[str] = "doc_msa_01"

@app.post("/api/integrations/slack/command")
async def handle_slack_command(req: SlackCommandRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Handles Slack slash command (/clauseverify) and returns Slack Block Kit formatted response."""
    workspace_plan = (current_user.get("workspace_plan") or "growth").lower()
    if workspace_plan == "starter":
        raise HTTPException(
            status_code=403,
            detail="⚡ Plan Gated: Slack Bot Integration (/clauseverify) requires a Growth ($799/mo) or Enterprise tier."
        )
    from server import search_and_verify
    res = search_and_verify(req.text, req.document_id, "Slack User (@alex_sales)")
    citation = res["citations"][0] if res.get("citations") and len(res["citations"]) > 0 else {}
    doc_title = "Acme Corp Master Services Agreement (MSA)"
    slack_blocks = integrations.format_slack_response(req.text, res["answer"], citation, doc_title)
    return slack_blocks

@app.post("/api/ocr/scan")
async def scan_physical_document(req: UploadRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """OCR Engine: Simulates processing flat scanned paper documents with wet-ink signatures."""
    workspace_plan = (current_user.get("workspace_plan") or "growth").lower()
    if workspace_plan in ["starter", "growth"]:
        raise HTTPException(
            status_code=403,
            detail="🔒 Plan Gated: Scanned Xerox and Wet-Ink OCR is an exclusive Enterprise tier capability ($1,999/mo)."
        )
    ocr_result = integrations.process_scanned_ocr_document(req.title)
    return ocr_result

@app.post("/api/questionnaire")
async def auto_fill_questionnaire(req: QuestionnaireRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Runs bulk security questionnaire verification."""
    workspace_plan = (current_user.get("workspace_plan") or "growth").lower()
    if workspace_plan == "starter":
        raise HTTPException(
            status_code=403,
            detail="⚡ Plan Gated: 1-Click Vendor Security Questionnaire Auto-Fill is available on Growth and Enterprise tiers. Please upgrade in the Pricing menu."
        )
    from server import process_questionnaire
    results = process_questionnaire(req.questions, req.document_id)
    return results

@app.get("/api/audit-logs")
async def get_audit_logs(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns immutable audit logs filtered by user's workspace."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM audit_logs 
    WHERE workspace_id = ? OR workspace_id IS NULL OR workspace_id = ''
    ORDER BY timestamp DESC LIMIT 50
    """, (current_user["workspace_id"],))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for r in rows:
        try:
            r["citations"] = json.loads(r["citations"])
        except Exception:
            pass
    return rows

# -------------------------------------------------------------
# Billing & Pricing Plans
# -------------------------------------------------------------
class SubscribeRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"

@app.get("/api/billing/plans")
async def get_plans(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns available subscription tiers and active workspace plan."""
    plans = [
        {
            "id": "starter",
            "name": "Starter",
            "tagline": "Ideal for seed/early-stage startups & boutique firms.",
            "monthly_price": 299,
            "annual_price": 239,
            "features": [
                "Up to 150 Active Contracts",
                "5 Team Seats",
                "Zero-Hallucination Visual Citations",
                "Amendment Drift Alerts",
                "Standard Audit Trail"
            ],
            "cta": "Start 14-Day Free Trial",
            "popular": False
        },
        {
            "id": "growth",
            "name": "Growth",
            "tagline": "For scaling B2B SaaS teams & compliance officers.",
            "monthly_price": 799,
            "annual_price": 639,
            "features": [
                "Unlimited Contracts & Policies",
                "15 Team Seats",
                "⚡ 1-Click Questionnaire Auto-Filler (CSV Export)",
                "Google Drive & SharePoint Sync",
                "Slack Bot Integration (/clauseverify)",
                "Immutable SOC 2 / ISO Audit Ledger",
                "Priority Email & Slack Support"
            ],
            "cta": "Upgrade to Growth",
            "popular": True
        },
        {
            "id": "enterprise",
            "name": "Enterprise",
            "tagline": "For FinTech, HealthTech, and regulated enterprises.",
            "monthly_price": 1999,
            "annual_price": 1599,
            "features": [
                "Everything in Growth",
                "Dedicated VPC / Isolated DB Tenant",
                "SAML 2.0 / Okta SSO & SCIM Directory",
                "Custom Scanned OCR Pipeline",
                "99.9% Uptime SLA Guarantee",
                "Dedicated Compliance Architect"
            ],
            "cta": "Contact Enterprise Sales",
            "popular": False
        }
    ]
    return {
        "plans": plans,
        "current_plan": "growth",
        "billing_cycle": "monthly",
        "trial_days_remaining": 14
    }

@app.post("/api/billing/subscribe")
async def update_subscription(req: SubscribeRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Simulates upgrading or subscribing to a plan."""
    conn = get_connection()
    cursor = conn.cursor()
    log_id = str(uuid.uuid4())
    cursor.execute("UPDATE workspaces SET plan = ? WHERE id = ?", (req.plan_id.lower(), current_user["workspace_id"]))
    cursor.execute("""
    INSERT INTO audit_logs (id, workspace_id, user_name, query, document_id, answer, citations, verified_match, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        current_user["workspace_id"],
        current_user["full_name"],
        f"Billing Plan Update: Switched to {req.plan_id.upper()} ({req.billing_cycle})",
        "billing_system",
        f"Workspace {current_user['workspace_name']} upgraded subscription tier to {req.plan_id.capitalize()}.",
        json.dumps([]),
        1,
        datetime.utcnow().isoformat() + "Z"
    ))
    conn.commit()
    conn.close()
    return {
        "success": True,
        "plan_id": req.plan_id,
        "billing_cycle": req.billing_cycle,
        "message": f"Successfully activated {req.plan_id.capitalize()} Plan for {current_user['workspace_name']}!"
    }

# -------------------------------------------------------------
# Static Web App Mount
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    print(f"============================================================")
    print(f"  ClauseVerify AI — Enterprise FastAPI Production Server")
    print(f"  Swagger Docs: http://localhost:{PORT}/docs")
    print(f"  App Dashboard: http://localhost:{PORT}/")
    print(f"============================================================")
    uvicorn.run("app:app", host="127.0.0.1", port=PORT, reload=False)
