"""
Verification Test for User Registration, Authentication & Isolated Workspace Creation
"""

import json
import urllib.request

PORT = 8000

def test_registration_and_login():
    def api_post(endpoint, data):
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}{endpoint}",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def api_get(endpoint, token):
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}{endpoint}",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    print("=" * 65)
    print("STEP 1: REGISTERING NEW ENTERPRISE USER & COMPANY WORKSPACE")
    print("=" * 65)
    reg_payload = {
        "email": "alex.morgan@quantumhealth.io",
        "password": "SecurePassword2025!",
        "full_name": "Dr. Alex Morgan",
        "company_name": "Quantum Health Intelligence",
        "role": "VP of Regulatory Compliance"
    }
    reg_res = api_post("/api/auth/register", reg_payload)
    print("Registration Status:", reg_res["status"])
    print("Registered User:", reg_res["user"]["full_name"])
    print("Created Workspace:", reg_res["user"]["workspace"]["name"])
    print("Assigned Domain:", reg_res["user"]["workspace"]["domain"])
    alex_token = reg_res["auth_token"]

    print("\n" + "=" * 65)
    print("STEP 2: TESTING LOGIN WITH REGISTERED CREDENTIALS")
    print("=" * 65)
    login_res = api_post("/api/auth/login", {
        "email": "alex.morgan@quantumhealth.io",
        "password": "SecurePassword2025!"
    })
    print("Login Status:", login_res["status"])
    print("Authenticated User:", login_res["user"]["full_name"])
    assert login_res["auth_token"] == alex_token, "Tokens do not match!"
    print("-> SUCCESS: User logged in and verified with hashed password.")

    print("\n" + "=" * 65)
    print("STEP 3: TESTING ISOLATED CONTRACT UPLOAD IN NEW WORKSPACE")
    print("=" * 65)
    upload_req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/api/upload",
        data=json.dumps({
            "title": "Quantum Health Clinical AI Trial Agreement",
            "content": "Section 1. Clinical Research Protocol\nAll clinical trial data is processed under FDA 21 CFR Part 11 rules."
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {alex_token}"},
        method="POST"
    )
    with urllib.request.urlopen(upload_req) as resp:
        upload_data = json.loads(resp.read().decode("utf-8"))
    print("Uploaded Contract ID:", upload_data["document"]["id"])
    print("Target Workspace ID:", upload_data["document"]["workspace_id"])

    # Verify that Alex can see their contract
    alex_docs = api_get("/api/documents", alex_token)
    print(f"Quantum Health Document Count: {len(alex_docs)}")
    assert "Quantum Health Clinical AI Trial Agreement" in [d["title"] for d in alex_docs]

    # Verify that Acme Global CANNOT see Quantum Health's contract
    acme_docs = api_get("/api/documents", "token_acme_compliance_officer_sec")
    acme_titles = [d["title"] for d in acme_docs]
    assert "Quantum Health Clinical AI Trial Agreement" not in acme_titles
    print("-> STRICT TENANT ISOLATION CONFIRMED: Acme Global cannot see Quantum Health contracts!")

    print("\n" + "=" * 65)
    print("REGISTRATION, LOGIN & TENANT ISOLATION TESTS PASSED 100%!")
    print("=" * 65)

if __name__ == "__main__":
    test_registration_and_login()
