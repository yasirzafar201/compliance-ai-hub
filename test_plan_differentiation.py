import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"
AUTH_TOKEN = "token_acme_compliance_officer_sec"

def make_req(endpoint, data=None, method="GET"):
    url = f"{BASE_URL}{endpoint}"
    encoded = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}"
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def run_tests():
    print("=== Testing Plan Differentiation & Tier Gating ===")

    # 1. Switch to Starter Plan
    print("\n[Step 1] Activating 'starter' plan...")
    status, res = make_req("/api/billing/subscribe", {"plan_id": "starter", "billing_cycle": "monthly"}, method="POST")
    print(f"Status: {status}, Message: {res.get('message')}")
    assert status == 200

    # 2. Test Starter Permissions
    print("\n[Step 2] Testing Starter permissions...")
    # Core search should work
    status, res = make_req("/api/query", {"query": "What is the uptime SLA?", "document_id": "doc_msa_01"}, method="POST")
    print(f"  Core Query (Allowed): Status {status} (Expected 200)")
    assert status == 200

    # Questionnaire Auto-Fill should be BLOCKED (403)
    status, res = make_req("/api/questionnaire", {"questions": ["Is MFA enforced?"], "document_id": "doc_soc2_02"}, method="POST")
    print(f"  Questionnaire Auto-Fill (Gated): Status {status} -> {res.get('detail')}")
    assert status == 403

    # Cloud Drive Sync should be BLOCKED (403)
    status, res = make_req("/api/integrations/cloud-sync", {"provider": "gdrive", "folder_index": 0}, method="POST")
    print(f"  Cloud Drive Sync (Gated): Status {status} -> {res.get('detail')}")
    assert status == 403

    # 3. Upgrade to Growth Plan
    print("\n[Step 3] Upgrading to 'growth' plan...")
    status, res = make_req("/api/billing/subscribe", {"plan_id": "growth", "billing_cycle": "annual"}, method="POST")
    print(f"Status: {status}, Message: {res.get('message')}")
    assert status == 200

    # 4. Test Growth Permissions
    print("\n[Step 4] Testing Growth permissions...")
    # Questionnaire Auto-Fill should now be UNLOCKED (200)
    status, res = make_req("/api/questionnaire", {"questions": ["Is MFA enforced?"], "document_id": "doc_soc2_02"}, method="POST")
    print(f"  Questionnaire Auto-Fill (Unlocked): Status {status} (Expected 200)")
    assert status == 200

    # Cloud Drive Sync should now be UNLOCKED (200)
    status, res = make_req("/api/integrations/cloud-sync", {"provider": "gdrive", "folder_index": 0}, method="POST")
    print(f"  Cloud Drive Sync (Unlocked): Status {status} (Expected 200)")
    assert status == 200

    # Scanned OCR should still be BLOCKED (Requires Enterprise)
    status, res = make_req("/api/ocr/scan", {"title": "Physical Deed Scan", "content": ""}, method="POST")
    print(f"  Scanned OCR (Enterprise Gated): Status {status} -> {res.get('detail')}")
    assert status == 403

    # 5. Upgrade to Enterprise Plan
    print("\n[Step 5] Upgrading to 'enterprise' plan...")
    status, res = make_req("/api/billing/subscribe", {"plan_id": "enterprise", "billing_cycle": "annual"}, method="POST")
    print(f"Status: {status}, Message: {res.get('message')}")
    assert status == 200

    # Scanned OCR should now be UNLOCKED (200)
    status, res = make_req("/api/ocr/scan", {"title": "Physical Deed Scan", "content": ""}, method="POST")
    print(f"  Scanned OCR (Unlocked): Status {status} (Expected 200)")
    assert status == 200

    print("\n✅ ALL TIER DIFFERENTIATION TESTS PASSED 100%!")

if __name__ == "__main__":
    run_tests()
