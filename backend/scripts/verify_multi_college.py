import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_verification():
    print("--- 1. Testing GET /health ---")
    res = client.get("/health")
    assert res.status_code == 200, f"Health endpoint failed: {res.text}"
    print(f"Health Response: {res.json()}")

    ts = int(time.time())
    print(f"\n--- 2. Testing Student Registration (Valid College Code DEMO001) ---")
    res = client.post("/api/v1/auth/student/register", json={
        "college_code": "DEMO001",
        "full_name": "Live Test Student",
        "email": f"livestudent_{ts}@demo001.edu",
        "password": "Password123!",
        "phone_number": "+919999888877"
    })
    assert res.status_code == 201, f"Student registration failed: {res.text}"
    student_data = res.json()
    print(f"Student Registered Successfully: ID={student_data['id']}, CollegeID={student_data['college_id']}")

    print("\n--- 3. Testing Student Login with college_code (Should NOT fail or trigger admin login) ---")
    res = client.post("/api/v1/auth/login", json={
        "email": f"livestudent_{ts}@demo001.edu",
        "password": "Password123!",
        "college_code": "DEMO001"
    })
    assert res.status_code == 200, f"Student login with college_code failed: {res.text}"
    print(f"Student Login with college_code Succeeded: Role={res.json()['role']}, CollegeID={res.json()['college_id']}")

    print("\n--- 4. Testing Student Login without college_code ---")
    res = client.post("/api/v1/auth/login", json={
        "email": f"livestudent_{ts}@demo001.edu",
        "password": "Password123!"
    })
    assert res.status_code == 200, f"Student login without college_code failed: {res.text}"
    print(f"Student Login without college_code Succeeded: Role={res.json()['role']}")

    print("\n--- 5. Testing Student Registration (Invalid College Code) ---")
    res = client.post("/api/v1/auth/student/register", json={
        "college_code": "INVALID_CODE_99",
        "full_name": "Invalid Student",
        "email": f"invalid_{ts}@demo.edu",
        "password": "Password123!"
    })
    assert res.status_code == 400, f"Expected 400 Bad Request, got {res.status_code}: {res.text}"
    print(f"Invalid College Code Rejected Correctly: {res.json()['detail']}")

    print("\n--- 6. Testing Admin Login (DEMO001 + Email + Password) ---")
    res = client.post("/api/v1/auth/admin/login", json={
        "college_code": "DEMO001",
        "email": "admin@demo001.edu",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    token_data = res.json()
    print(f"Admin Logged In Successfully: Token={token_data['access_token'][:15]}..., Role={token_data['role']}, CollegeID={token_data['college_id']}")

    print("\n--- 7. Testing Admin Login without college_code (Should return 401) ---")
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@demo001.edu",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 401, f"Expected 401 Unauthorized, got {res.status_code}"
    print("Admin Login without college_code Rejected Correctly.")

    print("\n--- 8. Testing Admin Login with Wrong College Code ---")
    res = client.post("/api/v1/auth/admin/login", json={
        "college_code": "DEMO002",
        "email": "admin@demo001.edu",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 401, f"Expected 401 Unauthorized, got {res.status_code}"
    print("Admin Login with Wrong College Code Rejected Correctly.")

    print("\n--- 9. Testing Authenticated /auth/me Profile ---")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_data['access_token']}"})
    assert res.status_code == 200, f"Profile fetch failed: {res.text}"
    profile = res.json()
    print(f"Profile Retrieved Successfully: {profile['full_name']} ({profile['role']}), CollegeID={profile['college_id']}")

    print("\nALL AUTHENTICATION BUG FIX VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
