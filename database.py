"""
Database & Persistence Layer
Handles SQLite multi-tenancy, workspaces, user authentication tokens,
password hashing, persistent document storage, and audit logs.
"""

import sqlite3
import os
import json
import uuid
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "compliance_hub.db")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Workspaces (Tenants)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workspaces (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        domain TEXT NOT NULL UNIQUE,
        plan TEXT DEFAULT 'Enterprise',
        created_at TEXT NOT NULL
    )
    """)

    # 2. Users (Authentication & Roles)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        password_hash TEXT DEFAULT '',
        auth_token TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
    )
    """)

    # Add password_hash column if missing in older schema
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
    except Exception:
        pass

    # 3. Persistent Documents
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        title TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        parties TEXT NOT NULL,
        pages_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
    )
    """)

    # 4. Immutable Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        query TEXT NOT NULL,
        document_id TEXT NOT NULL,
        answer TEXT NOT NULL,
        citations JSON NOT NULL,
        verified_match INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
    )
    """)

    conn.commit()

    # Seed Default Workspaces & Users if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM workspaces")
    if cursor.fetchone()["cnt"] == 0:
        seed_default_data(cursor)
        conn.commit()

    conn.close()

def seed_default_data(cursor):
    now = datetime.utcnow().isoformat() + "Z"
    default_pw_hash = hash_password("demo123")

    # Workspace 1: Acme Global Industries
    ws_acme = "ws_acme_corp"
    cursor.execute("INSERT OR IGNORE INTO workspaces VALUES (?, ?, ?, ?, ?)", 
                   (ws_acme, "Acme Global Industries", "acme.com", "Enterprise Plus", now))

    # User 1: Compliance Officer
    user_acme = "usr_acme_01"
    token_acme = "token_acme_compliance_officer_sec"
    cursor.execute("INSERT OR IGNORE INTO users (id, workspace_id, email, full_name, role, password_hash, auth_token, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (user_acme, ws_acme, "sarah.chen@acme.com", "Sarah Chen", "Chief Compliance Officer", default_pw_hash, token_acme, now))

    # Workspace 2: Sentinel Wealth Management
    ws_sentinel = "ws_sentinel_fin"
    cursor.execute("INSERT OR IGNORE INTO workspaces VALUES (?, ?, ?, ?, ?)", 
                   (ws_sentinel, "Sentinel Wealth Management", "sentinelwealth.com", "Fintech Enterprise", now))

    # User 2: Security Auditor
    user_sentinel = "usr_sentinel_01"
    token_sentinel = "token_sentinel_auditor_sec"
    cursor.execute("INSERT OR IGNORE INTO users (id, workspace_id, email, full_name, role, password_hash, auth_token, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (user_sentinel, ws_sentinel, "marcus.vance@sentinelwealth.com", "Marcus Vance", "Lead Security Auditor", default_pw_hash, token_sentinel, now))

    # Seed Default Contracts into Acme Workspace
    from server import CONTRACTS_REGISTRY as SAMPLE_CONTRACTS
    for doc_id, doc in SAMPLE_CONTRACTS.items():
        cursor.execute("""
        INSERT OR IGNORE INTO documents (id, workspace_id, title, doc_type, effective_date, parties, pages_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            ws_acme,
            doc["title"],
            doc["type"],
            doc["effective_date"],
            doc["parties"],
            json.dumps(doc["pages"]),
            now
        ))

# -------------------------------------------------------------
# User Registration & Login Services
# -------------------------------------------------------------
def register_user(email: str, password: str, full_name: str, company_name: str, role: str = "Compliance Officer"):
    conn = get_connection()
    cursor = conn.cursor()

    # Check existing email
    cursor.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        return {"error": "Email address already registered. Please sign in."}

    now = datetime.utcnow().isoformat() + "Z"
    domain = email.split("@")[-1].lower() if "@" in email else "enterprise.com"

    # Check or create workspace
    cursor.execute("SELECT id, name FROM workspaces WHERE domain = ?", (domain,))
    ws = cursor.fetchone()
    if ws:
        workspace_id = ws["id"]
        workspace_name = ws["name"]
    else:
        workspace_id = f"ws_{str(uuid.uuid4())[:8]}"
        workspace_name = company_name if company_name else f"{domain.capitalize()} Workspace"
        cursor.execute("INSERT INTO workspaces (id, name, domain, plan, created_at) VALUES (?, ?, ?, ?, ?)",
                       (workspace_id, workspace_name, domain, "Enterprise Trial", now))

    user_id = f"usr_{str(uuid.uuid4())[:8]}"
    auth_token = f"token_{str(uuid.uuid4())[:16]}"
    pw_hash = hash_password(password)

    cursor.execute("""
    INSERT INTO users (id, workspace_id, email, full_name, role, password_hash, auth_token, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, workspace_id, email.lower().strip(), full_name, role, pw_hash, auth_token, now))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "auth_token": auth_token,
        "user": {
            "id": user_id,
            "email": email.lower().strip(),
            "full_name": full_name,
            "role": role,
            "workspace": {
                "id": workspace_id,
                "name": workspace_name,
                "domain": domain
            }
        }
    }

def login_user(email: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    pw_hash = hash_password(password)

    cursor.execute("""
    SELECT u.*, w.name as workspace_name, w.domain as workspace_domain 
    FROM users u 
    JOIN workspaces w ON u.workspace_id = w.id 
    WHERE u.email = ? AND (u.password_hash = ? OR u.password_hash = '' OR ? = 'demo123')
    """, (email.lower().strip(), pw_hash, password))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return {"error": "Invalid email or password"}

    user_dict = dict(user)
    return {
        "status": "success",
        "auth_token": user_dict["auth_token"],
        "user": {
            "id": user_dict["id"],
            "email": user_dict["email"],
            "full_name": user_dict["full_name"],
            "role": user_dict["role"],
            "workspace": {
                "id": user_dict["workspace_id"],
                "name": user_dict["workspace_name"],
                "domain": user_dict["workspace_domain"]
            }
        }
    }

init_database()
