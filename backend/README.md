# VeriCampus AI — Backend Service

FastAPI backend for VeriCampus AI — AI-Powered Scholarship Document Verification & Workflow Automation Platform.

## Current Architecture: Multi-College Tenancy & Authentication

### Features & Infrastructure
- **FastAPI Application**: Standard REST framework with OpenAPI documentation, CORS middleware, and `GET /health` monitoring.
- **Multi-College Tenancy**:
  - `College` model (`id`, `college_name`, `college_code` [UNIQUE], `email`, `address`, `is_active`)
  - `AdminOfficer` bound to exactly ONE college with database-enforced `UNIQUE` constraint on `college_id`
  - `Student` bound to exactly ONE college (`college_id`)
- **SQLAlchemy 2.0 Declarative ORM Models**: `College`, `Student`, `AdminOfficer`, `ScholarshipApplication`, `Document`, `VerificationResult`, `PhysicalVerificationAppointment`
- **Pydantic v2 Schemas**: Serialization, domain validation, and JWT payload models with `from_attributes=True` compatibility
- **Alembic Database Migrations**: Sequential migrations (`001_initial_schema`, `2416706cec79`, `d0c676a58d4b_add_multi_college_support`) applied to local PostgreSQL (`vericampus`)
- **Authentication Infrastructure & Security Service (`AuthService`)**:
  - Salted bcrypt password hashing & verification
  - Signed JWT access-token creation & validation with embedded `college_id` claim
  - Admin login requiring **College Code + Email + Password**
  - Student registration requiring valid **College Code**
  - HTTP Bearer token dependencies (`get_current_token_payload`, `require_admin_user`)
- **API Endpoints (`/api/v1/auth`)**:
  1. `POST /api/v1/auth/student/register` — Student Registration (Requires valid `college_code`)
  2. `POST /api/v1/auth/admin/login` — Dedicated Admin Login (Requires `college_code` + `email` + `password`)
  3. `POST /api/v1/auth/login` — Unified Login Endpoint
  4. `GET /api/v1/auth/me` — Authenticated User Profile (Returns user details with `college_id`)
- **Comprehensive Test Suite**: 39 out of 39 automated tests passing cleanly in `backend/tests/`.

---

## Authentication Endpoints & Usage

### 1. Student Registration
- **Endpoint**: `POST /api/v1/auth/student/register`
- **Request Body**:
  ```json
  {
    "college_code": "DEMO001",
    "full_name": "Rahul Sharma",
    "email": "rahul.sharma@example.edu",
    "password": "SecurePassword123!",
    "phone_number": "+919876543210",
    "address": "Pune, Maharashtra"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
    "college_id": "3649c76f-9e0b-4dd7-b971-117348dc83e5",
    "full_name": "Rahul Sharma",
    "email": "rahul.sharma@example.edu",
    "phone_number": "+919876543210",
    "government_id_number": null,
    "date_of_birth": null,
    "address": "Pune, Maharashtra",
    "created_at": "2026-09-18T12:00:00Z",
    "updated_at": "2026-09-18T12:00:00Z"
  }
  ```

### 2. Admin Officer Login
- **Endpoint**: `POST /api/v1/auth/admin/login`
- **Request Body**:
  ```json
  {
    "college_code": "DEMO001",
    "email": "admin@demo001.edu",
    "password": "AdminPassword123!"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user_id": "d1a8f98a-2394-4d82-841a-bb09472391b1",
    "college_id": "3649c76f-9e0b-4dd7-b971-117348dc83e5",
    "email": "admin@demo001.edu",
    "role": "ADMIN",
    "expires_in_seconds": 86400
  }
  ```

### 3. Get Authenticated User Profile
- **Endpoint**: `GET /api/v1/auth/me`
- **Header**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  {
    "id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
    "college_id": "3649c76f-9e0b-4dd7-b971-117348dc83e5",
    "full_name": "Rahul Sharma",
    "email": "rahul.sharma@example.edu",
    "role": "STUDENT",
    "phone_number": "+919876543210",
    "department": null,
    "designation": null,
    "is_active": true
  }
  ```

---

## Setup & Execution

### 1. Environment Setup & Dependencies
```bash
cd backend
python -m venv venv

# Activate Virtual Environment:
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
```

### 2. Database & Security Configuration
Copy `.env.example` to `.env` and configure local environment variables:
```env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/vericampus
JWT_SECRET_KEY=your-custom-secure-random-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 3. Database Seed & Migrations
```bash
# Run database migrations
alembic upgrade head

# Seed development colleges (DEMO001 and DEMO002) and admin accounts
python -m app.db.seed
```

### 4. Running Backend Tests
```bash
python -m unittest discover -s tests
```

### 5. Running Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
