"""
Enterprise Multi-Tenancy & FastAPI Verification Test
"""

import json
import urllib.request
import threading
import time
import uvicorn
import database
import app

def run_tests():
    PORT = 8098
    config = uvicorn.Config(app.app, host="127.0.0.1", port=PORT, log_level="warning")
    server_instance = uvicorn.Server(config)

    t = threading.Thread(target=server_instance.run, daemon=True)
    t.start()
    time.sleep(1.5)

    def api_get(endpoint, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(f'http://127.0.0.1:{PORT}{endpoint}', headers=headers)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def api_post(endpoint, data, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(f'http://127.0.0.1:{PORT}{endpoint}', data=json.dumps(data).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    print("=" * 65)
    print("STEP 1: TESTING AUTH & TENANT IDENTITY (/api/auth/me)")
    print("=" * 65)
    user_acme = api_get("/api/auth/me", token="token_acme_compliance_officer_sec")
    print("Logged In User:", user_acme["full_name"])
    print("Role:", user_acme["role"])
    print("Workspace:", user_acme["workspace"]["name"], f"({user_acme['workspace']['domain']})")

    print("\n" + "=" * 65)
    print("STEP 2: TESTING PERSISTENT UPLOAD FOR ACME WORKSPACE")
    print("=" * 65)
    upload_res = api_post("/api/upload", {
        "title": "Acme Confidential Vendor Addendum 2025",
        "content": "Section 1. Minimum Order Quantity\nAcme guarantees minimum annual volume of 50,000 units.\n\nSection 2. Pricing Discount\nTier 1 pricing provides 15% discount on Net 30 payments."
    }, token="token_acme_compliance_officer_sec")
    acme_doc_id = upload_res["document"]["id"]
    print("Uploaded Contract ID:", acme_doc_id)
    print("Assigned Workspace ID:", upload_res["document"]["workspace_id"])

    # Verify Acme documents list has this document
    acme_docs = api_get("/api/documents", token="token_acme_compliance_officer_sec")
    acme_titles = [d["title"] for d in acme_docs]
    print(f"Acme Workspace Document Count: {len(acme_docs)}")
    assert "Acme Confidential Vendor Addendum 2025" in acme_titles, "Doc not found in Acme workspace"
    print("-> Confirmed document is present in Acme Global workspace.")

    print("\n" + "=" * 65)
    print("STEP 3: TESTING STRICT TENANT ISOLATION (SENTINEL WEALTH)")
    print("=" * 65)
    # Switch to Marcus Vance (Sentinel Wealth Management)
    sentinel_user = api_get("/api/auth/me", token="token_sentinel_auditor_sec")
    print("Switched User:", sentinel_user["full_name"])
    print("Switched Workspace:", sentinel_user["workspace"]["name"])

    # Marcus should NOT see Acme's uploaded document!
    sentinel_docs = api_get("/api/documents", token="token_sentinel_auditor_sec")
    sentinel_titles = [d["title"] for d in sentinel_docs]
    print(f"Sentinel Workspace Document Count: {len(sentinel_docs)}")
    print("Sentinel Document Titles:", sentinel_titles)

    assert "Acme Confidential Vendor Addendum 2025" not in sentinel_titles, "SECURITY BREACH: Acme doc leaked to Sentinel!"
    print("-> VERIFIED: Sentinel Wealth CANNOT see Acme's confidential documents! Strict tenant isolation confirmed.")

    print("\n" + "=" * 65)
    print("STEP 4: TESTING PERSISTENCE IN SQLITE DATABASE")
    print("=" * 65)
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, workspace_id, created_at FROM documents WHERE id = ?", (acme_doc_id,))
    db_row = cursor.fetchone()
    conn.close()
    print("Row fetched from SQLite on disk:")
    print("  Title:", db_row["title"])
    print("  Workspace ID:", db_row["workspace_id"])
    print("  Timestamp:", db_row["created_at"])
    print("-> Contract is permanently stored in database and will survive server restarts.")

    print("\n" + "=" * 65)
    print("ALL ENTERPRISE PRODUCTION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

    server_instance.should_exit = True

if __name__ == "__main__":
    run_tests()
