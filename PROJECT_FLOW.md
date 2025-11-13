# HRMS SaaS Backend - Project Flow Documentation

## 📋 Table of Contents
1. [Application Architecture](#application-architecture)
2. [Company Registration Flow](#company-registration-flow)
3. [Database Schema](#database-schema)
4. [API Request Flow](#api-request-flow)
5. [Authentication Flow](#authentication-flow)
6. [Project Structure](#project-structure)

---

## 🏗️ Application Architecture

### **Application Startup Flow**

```
1. Server Starts (uvicorn/app.main.py)
   ↓
2. FastAPI App Initialization
   ↓
3. Database Connection Test
   ↓
4. Create/Verify Database Tables
   ↓
5. Include API Routes (app/api/router.py)
   ↓
6. Server Ready on http://localhost:8000
```

### **Route Registration Flow**

```
app/main.py
  └── includes api_router with prefix "/api/v1"
      │
      └── app/api/router.py
          ├── auth.router (prefix="/auth")
          ├── employees.router
          ├── departments.router
          └── tasks.router
```

**Final Endpoint URLs:**
- Company Registration: `POST /api/v1/auth/register-company`
- User Login: `POST /api/v1/auth/login`
- Get Current User: `GET /api/v1/auth/me`
- Change Password: `POST /api/v1/auth/change-password`

---

## 🏢 Company Registration Flow

### **Overview**
The company registration API is the **main entry point** for the HRMS system. When a company registers, it creates:
1. A **Company** record in the `companies` table
2. An **Admin User** record in the `users` table

### **Step-by-Step Registration Process**

#### **Step 1: Client Request**
```http
POST /api/v1/auth/register-company
Content-Type: application/json

{
  "company_name": "Tech Solutions Inc",
  "company_email": "contact@techsolutions.com",
  "company_phone": "+1-555-0123",
  "company_address": "123 Business St, City, State",
  "company_type": "Private Limited",
  "company_type_other": null,
  "company_gst_number": "27AABCU9603R1ZX",
  "company_pan_number": "AABCU9603R",
  "admin_full_name": "John Admin",
  "admin_email": "john.admin@techsolutions.com",
  "admin_username": "johnadmin",
  "company_password": "SecurePass123"
}
```

#### **Step 2: Request Validation**
**Location:** `app/api/v1/routes/auth.py` → `register_company()`

- FastAPI validates the request body against `CompanyRegister` schema
- Schema validation ensures:
  - `company_name`: 2-255 characters
  - `company_email`: Valid email format
  - `company_phone`: Optional, max 20 characters
  - `company_address`: Optional
  - `company_type`: Dropdown selection (Solo Proprietor, Organization, Private Limited, LLP, Partnership, Public Limited, Other)
  - `company_type_other`: Required if company_type is "Other"
  - `company_gst_number`: Optional, max 50 characters
  - `company_pan_number`: Required, max 50 characters
  - `admin_full_name`: 2-255 characters
  - `admin_email`: Valid email format
  - `admin_username`: 3-50 characters, unique
  - `company_password`: Minimum 6 characters

#### **Step 3: Service Layer Processing**
**Location:** `app/api/v1/services/auth_service.py` → `AuthService.register_company()`

**Process Flow:**

```
1. Check if company_email already exists in companies table
   └── If exists → Return 400 Error: "Company email already registered"
   
2. Check if admin_username already exists in users table
   └── If exists → Return 400 Error: "Username already taken"
   
3. Check if admin_email already exists in users table
   └── If exists → Return 400 Error: "Admin email already registered"
   
4. Generate unique company_code (format: CMP00000001)
   └── Function: generate_company_code()
   └── Finds last company, extracts number, increments
   └── Formats as CMP + 8-digit number
   
5. Create Company Record
   └── Table: companies
   └── Fields:
       - company_code: "CMP00000001" (auto-generated)
       - company_name: From request
       - email: company_email from request
       - phone: company_phone from request (optional)
       - address: company_address from request (optional)
       - company_type: From request (enum: Solo Proprietor, Organization, Private Limited, LLP, Partnership, Public Limited, Other)
       - company_type_other: Custom type if company_type is "Other" (optional)
       - gst_number: company_gst_number from request (optional)
       - pan_number: company_pan_number from request (required)
       - is_active: True (default)
       - created_at: Current timestamp
       - updated_at: Current timestamp
   
6. Flush to database (get company.id without committing)
   └── This ensures we have company_id for the admin user
   
7. Create Admin User Record
   └── Table: users
   └── Fields:
       - company_id: From newly created company.id
       - email: admin_email from request
       - username: admin_username from request
       - full_name: admin_full_name from request
       - hashed_password: bcrypt hash of company_password
       - role: UserRole.ADMIN
       - is_active: True
       - is_superuser: False
       - force_password_change: False
       - created_at: Current timestamp
       - updated_at: Current timestamp
   
8. Commit transaction
   └── Both Company and User records saved atomically
   
9. Refresh objects from database
   └── Ensures all fields are populated (IDs, timestamps)
   
10. Return (company, admin_user) tuple
```

#### **Step 4: Response Generation**
**Location:** `app/api/v1/routes/auth.py` → `register_company()`

```python
return CompanyRegistrationResponse(
    company=company,              # CompanyResponse object
    admin_username=admin_user.username,
    message="Company registered successfully! Admin can now login."
)
```

**Response JSON:**
```json
{
  "company": {
    "id": 1,
    "company_code": "CMP00000001",
    "company_name": "Tech Solutions Inc",
    "email": "contact@techsolutions.com",
    "phone": "+1-555-0123",
    "address": "123 Business St, City, State",
    "company_type": "Private Limited",
    "company_type_other": null,
    "gst_number": "27AABCU9603R1ZX",
    "pan_number": "AABCU9603R",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "admin_username": "johnadmin",
  "message": "Company registered successfully! Admin can now login."
}
```

---

## 🗄️ Database Schema

### **Companies Table (`companies`)**

**Purpose:** Stores company/client information (multi-tenant architecture)

**Table Structure:**
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    company_code VARCHAR(50) UNIQUE NOT NULL,  -- Auto-generated: CMP00000001
    company_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,        -- Company email
    phone VARCHAR(20),                         -- Optional
    address TEXT,                              -- Optional
    company_type VARCHAR(50) NOT NULL,         -- Enum: Solo Proprietor, Organization, Private Limited, LLP, Partnership, Public Limited, Other
    company_type_other VARCHAR(255),            -- Custom type when "Other" is selected
    gst_number VARCHAR(50),                     -- Optional, indexed
    pan_number VARCHAR(50) NOT NULL,            -- Required, indexed
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Key Fields:**
- `id`: Primary key, auto-increment
- `company_code`: Unique identifier (CMP00000001, CMP00000002, ...)
- `email`: Unique company email (used for duplicate checking)
- `company_type`: Company type enum (dropdown selection)
- `company_type_other`: Custom company type when "Other" is selected
- `gst_number`: Company GST number (optional, indexed for search)
- `pan_number`: Company PAN number (required, indexed for search)
- `is_active`: Controls if company can access the system

**Relationships:**
- One Company → Many Users (via `users.company_id`)
- One Company → Many Employees (via `employees.company_id`)
- One Company → Many Departments (via `departments.company_id`)

### **Users Table (`users`)**

**Purpose:** Stores authentication credentials for admins and employees

**Table Structure:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,     -- bcrypt hash
    role VARCHAR(20) NOT NULL,                 -- 'admin' or 'employee'
    employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    force_password_change BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Key Fields:**
- `company_id`: Foreign key to companies table (required)
- `username`: Unique login username
- `email`: Unique email address
- `hashed_password`: Bcrypt hashed password (never store plain text)
- `role`: Enum - either 'admin' or 'employee'
- `employee_id`: Optional link to employee record (for employees)

**During Registration:**
- Admin user is created with `role = 'admin'`
- `company_id` links to the newly created company
- `employee_id` is NULL for admin users

---

## 🔄 API Request Flow

### **Complete Request-Response Cycle**

```
┌─────────────────┐
│   Client/User   │
└────────┬────────┘
         │
         │ POST /api/v1/auth/register-company
         │ { company_name, company_email, ... }
         │
         ▼
┌─────────────────────────────────┐
│   FastAPI Application           │
│   (app/main.py)                 │
└────────┬────────────────────────┘
         │
         │ Route: /api/v1/auth/register-company
         │
         ▼
┌─────────────────────────────────┐
│   Auth Router                   │
│   (app/api/v1/routes/auth.py)  │
│   register_company()            │
└────────┬────────────────────────┘
         │
         │ Validate: CompanyRegister schema
         │
         ▼
┌─────────────────────────────────┐
│   Auth Service                  │
│   (app/api/v1/services/         │
│    auth_service.py)             │
│   AuthService.register_company() │
└────────┬────────────────────────┘
         │
         │ 1. Check duplicates
         │ 2. Generate company_code
         │ 3. Create Company record
         │ 4. Create Admin User record
         │ 5. Commit transaction
         │
         ▼
┌─────────────────────────────────┐
│   Database (PostgreSQL)         │
│   - companies table             │
│   - users table                 │
└────────┬────────────────────────┘
         │
         │ Return: (company, admin_user)
         │
         ▼
┌─────────────────────────────────┐
│   Response Formatter            │
│   CompanyRegistrationResponse   │
└────────┬────────────────────────┘
         │
         │ JSON Response
         │
         ▼
┌─────────────────┐
│   Client/User   │
│   Receives:     │
│   - company info│
│   - admin_username│
│   - success msg │
└─────────────────┘
```

### **Error Handling Flow**

```
Request → Validation Error
  └── FastAPI returns 422 (Unprocessable Entity)
      └── Shows which fields failed validation

Request → Duplicate Email/Username
  └── AuthService checks database
      └── Returns 400 (Bad Request)
          └── "Company email already registered"
          └── "Username already taken"
          └── "Admin email already registered"

Request → Database Error
  └── Transaction rollback
      └── Returns 500 (Internal Server Error)
          └── "Failed to register company: {error}"
```

---

## 🔐 Authentication Flow

### **After Registration - Login Flow**

```
1. Admin receives registration response with username
   ↓
2. Admin calls POST /api/v1/auth/login
   {
     "username": "johnadmin",
     "password": "SecurePass123"
   }
   ↓
3. AuthService.authenticate_user() validates credentials
   ↓
4. JWT token generated with:
   {
     "sub": "johnadmin",
     "user_id": 1,
     "company_id": 1,
     "role": "admin"
   }
   ↓
5. Response includes access_token
   ↓
6. Admin uses token in Authorization header:
   Authorization: Bearer <token>
   ↓
7. All subsequent API calls include this token
   ↓
8. get_current_user() dependency validates token
   ↓
9. Returns authenticated user object
```

### **Token-Based Authentication**

**Token Creation:**
- Location: `app/core/security.py` → `create_access_token()`
- Algorithm: HS256
- Expiration: Configurable (default: 30 minutes)
- Contains: username, user_id, company_id, role

**Token Validation:**
- Location: `app/api/v1/dependencies.py` → `get_current_user()`
- Decodes JWT token
- Retrieves user from database
- Checks user and company active status
- Returns User object for route handlers

---

## 📁 Project Structure

### **File Organization**

```
hrms_saas_backend/
│
├── app/
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/
│   │   ├── router.py              # Main API router
│   │   │
│   │   └── v1/
│   │       ├── routes/
│   │       │   └── auth.py        # Auth endpoints (register, login)
│   │       │
│   │       ├── models/
│   │       │   ├── company_model.py  # Company SQLAlchemy model
│   │       │   └── user_model.py     # User SQLAlchemy model
│   │       │
│   │       ├── schemas/
│   │       │   ├── company_schema.py  # Company Pydantic schemas
│   │       │   └── user_schema.py     # User Pydantic schemas
│   │       │
│   │       └── services/
│   │           └── auth_service.py   # Business logic for auth
│   │
│   ├── core/
│   │   ├── config.py              # Settings and configuration
│   │   └── security.py            # JWT, password hashing
│   │
│   └── db/
│       ├── base.py                # SQLAlchemy Base
│       └── session.py             # Database session management
│
└── PROJECT_FLOW.md                # This file
```

### **Key Components**

**Models (`app/api/v1/models/`):**
- Define database table structure
- SQLAlchemy ORM classes
- Relationships between tables

**Schemas (`app/api/v1/schemas/`):**
- Pydantic models for request/response validation
- Data serialization/deserialization
- API contract definition

**Routes (`app/api/v1/routes/`):**
- FastAPI route handlers
- HTTP endpoint definitions
- Request/response handling

**Services (`app/api/v1/services/`):**
- Business logic layer
- Database operations
- Data validation and processing

---

## 🔑 Key Concepts

### **Multi-Tenant Architecture**
- Each company is isolated by `company_id`
- All users, employees, departments linked to a company
- Data separation at database level

### **Company Code Generation**
- Auto-generated unique identifier
- Format: `CMP` + 8-digit number
- Example: `CMP00000001`, `CMP00000002`
- Ensures uniqueness across all companies

### **Password Security**
- Passwords are **never** stored in plain text
- Bcrypt hashing algorithm
- One-way encryption (cannot be reversed)
- Hash comparison for authentication

### **Transaction Safety**
- Company and Admin User creation in single transaction
- If either fails, entire operation rolls back
- Ensures data consistency

---

## 📝 Summary

**Company Registration Process:**
1. Client sends POST request with company and admin details
2. FastAPI validates request schema
3. AuthService checks for duplicates
4. Unique company_code generated
5. Company record created in `companies` table
6. Admin user record created in `users` table
7. Transaction committed atomically
8. Response returned with company info and admin username

**After Registration:**
- Admin can login with username/password
- Receives JWT token for authentication
- Can manage company employees, departments, tasks
- All operations scoped to their company

**Database Tables:**
- `companies`: Stores company/client information
- `users`: Stores authentication credentials (admin and employees)

This architecture ensures secure, multi-tenant HRMS functionality where each company's data is isolated and managed independently.

