# HRMS Multi-Tenant Implementation Guide

## 🎯 Overview

This HRMS (Human Resource Management System) now supports a **multi-tenant architecture** where:

1. **Companies register first** with an admin user
2. **Admins add employees** to their company
3. **Employees get login credentials** and can access the employee portal
4. **Complete role-based access control** (Admin vs Employee)
5. **Company data isolation** - each company only sees their own data

---

## 🔄 Complete Flow

### **Phase 1: Company Registration**

```
Company Admin → Register Company → System Creates:
  1. Company record
  2. Admin user with role=ADMIN
  
Admin can now login and manage their company
```

### **Phase 2: Admin Adds Employees**

```
Admin logs in → Add Employee → System Creates:
  1. Employee record
  2. User account (role=EMPLOYEE)
  3. Initial password (force_password_change=true)
  
Employee receives credentials
```

### **Phase 3: Employee Login & Portal**

```
Employee logs in → Prompted to change password → Access Portal:
  - View profile
  - Change password
  - View attendance, payroll, etc.
```

---

## 🗄️ Database Schema

### **Companies Table**
- `id` - Primary key
- `company_name` - Company name
- `email` - Company email (unique)
- `phone` - Company phone
- `address` - Company address
- `is_active` - Active status
- `created_at`, `updated_at` - Timestamps

### **Users Table** (Authentication)
- `id` - Primary key
- `company_id` - Foreign key → companies.id
- `email` - User email (unique)
- `username` - Username (unique)
- `full_name` - User's full name
- `hashed_password` - Encrypted password
- `role` - Enum: 'admin' or 'employee'
- `employee_id` - Foreign key → employees.id (nullable, for employees only)
- `is_active` - Active status
- `force_password_change` - Boolean flag for first-time login
- `created_at`, `updated_at` - Timestamps

### **Employees Table**
- `id` - Primary key
- `company_id` - Foreign key → companies.id
- `department_id` - Foreign key → departments.id
- `employee_code` - Unique employee code
- `first_name`, `last_name` - Employee name
- `email` - Employee email (unique)
- `phone` - Phone number
- `date_of_birth` - DOB
- `position` - Job title
- `hire_date` - Date of hire
- `salary` - Employee salary
- `is_active` - Active status
- `created_at`, `updated_at` - Timestamps

### **Departments Table**
- `id` - Primary key
- `company_id` - Foreign key → companies.id
- `name` - Department name
- `description` - Department description
- `is_active` - Active status
- `created_at`, `updated_at` - Timestamps

---

## 🔐 Authentication & Authorization

### **Roles**
- **ADMIN**: Company administrators - full control over their company
- **EMPLOYEE**: Regular employees - limited access to their own data

### **Access Control Dependencies**
```python
# Anyone authenticated
current_user = Depends(get_current_user)

# Admin only
current_user = Depends(require_admin)

# Employee only
current_user = Depends(require_employee)
```

### **JWT Token Contents**
```json
{
  "sub": "username",
  "user_id": 123,
  "company_id": 45,
  "role": "admin"
}
```

---

## 📡 API Endpoints

### **Authentication Endpoints**

#### 1. Register Company (New Main Registration)
```http
POST /api/v1/auth/register-company
Content-Type: application/json

{
  "company_name": "Tech Corp",
  "company_email": "admin@techcorp.com",
  "company_phone": "+1234567890",
  "company_address": "123 Main St",
  "admin_full_name": "John Admin",
  "admin_email": "john@techcorp.com",
  "admin_username": "johnadmin",
  "admin_password": "SecurePass123"
}

Response:
{
  "company": {
    "id": 1,
    "company_name": "Tech Corp",
    "email": "admin@techcorp.com",
    ...
  },
  "admin_username": "johnadmin",
  "message": "Company registered successfully! Admin can now login."
}
```

#### 2. Login (Admin & Employee)
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "johnadmin",
  "password": "SecurePass123"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "company_id": 1,
    "username": "johnadmin",
    "email": "john@techcorp.com",
    "full_name": "John Admin",
    "role": "admin",
    "is_active": true,
    "force_password_change": false,
    ...
  }
}
```

#### 3. Get Current User Info
```http
GET /api/v1/auth/me
Authorization: Bearer <token>

Response:
{
  "id": 1,
  "company_id": 1,
  "username": "johnadmin",
  "role": "admin",
  ...
}
```

#### 4. Change Password
```http
POST /api/v1/auth/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "TempPass123",
  "new_password": "NewSecurePass456",
  "confirm_password": "NewSecurePass456"
}

Response:
{
  "message": "Password changed successfully"
}
```

### **Employee Endpoints (Admin)**

#### 5. Create Employee
```http
POST /api/v1/employees
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "employee_code": "EMP001",
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane.doe@techcorp.com",
  "phone": "+1234567890",
  "position": "Software Engineer",
  "hire_date": "2025-01-15",
  "initial_password": "TempPass123",
  "department_id": 1,
  "salary": 75000.00
}

Response:
{
  "employee": {
    "id": 1,
    "company_id": 1,
    "employee_code": "EMP001",
    "full_name": "Jane Doe",
    ...
  },
  "username": "emp001",
  "temp_password": "TempPass123",
  "message": "Employee created successfully. Please share credentials with the employee."
}
```

#### 6. Get All Employees
```http
GET /api/v1/employees?skip=0&limit=50&is_active=true
Authorization: Bearer <token>

Response:
[
  {
    "id": 1,
    "company_id": 1,
    "employee_code": "EMP001",
    "full_name": "Jane Doe",
    ...
  },
  ...
]
```

#### 7. Get Employee by ID
```http
GET /api/v1/employees/1
Authorization: Bearer <token>
```

#### 8. Update Employee
```http
PUT /api/v1/employees/1
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "position": "Senior Software Engineer",
  "salary": 85000.00
}
```

#### 9. Deactivate Employee
```http
DELETE /api/v1/employees/1
Authorization: Bearer <admin-token>
```

### **Department Endpoints**

#### 10. Create Department
```http
POST /api/v1/departments
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "name": "Engineering",
  "description": "Software engineering team"
}
```

#### 11. Get All Departments
```http
GET /api/v1/departments?skip=0&limit=50
Authorization: Bearer <token>
```

#### 12. Update Department
```http
PUT /api/v1/departments/1
Authorization: Bearer <admin-token>
```

#### 13. Deactivate Department
```http
DELETE /api/v1/departments/1
Authorization: Bearer <admin-token>
```

---

## 🚀 Setup & Migration

### **Step 1: Drop and Recreate Database**

Since we've made significant schema changes, the easiest approach is to recreate the database:

```bash
# Drop existing tables and create new ones
python create_tables.py
```

Or manually:
```python
from app.db.session import engine
from app.db.base import Base

# Drop all tables
Base.metadata.drop_all(bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)
```

### **Step 2: Start the Server**

```bash
# Using the start script
./start_server.sh

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### **Step 3: Test the Flow**

1. **Register a company**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register-company" \
        -H "Content-Type: application/json" \
        -d '{
          "company_name": "Test Corp",
          "company_email": "admin@testcorp.com",
          "admin_full_name": "Admin User",
          "admin_email": "admin@testcorp.com",
          "admin_username": "admin",
          "admin_password": "password123"
        }'
   ```

2. **Login as admin**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "password123"}'
   ```

3. **Create a department** (using admin token):
   ```bash
   curl -X POST "http://localhost:8000/api/v1/departments" \
        -H "Authorization: Bearer <admin-token>" \
        -H "Content-Type: application/json" \
        -d '{"name": "Engineering", "description": "Tech team"}'
   ```

4. **Add an employee**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/employees" \
        -H "Authorization: Bearer <admin-token>" \
        -H "Content-Type: application/json" \
        -d '{
          "employee_code": "EMP001",
          "first_name": "John",
          "last_name": "Employee",
          "email": "john@testcorp.com",
          "hire_date": "2025-01-15",
          "initial_password": "temp123",
          "department_id": 1
        }'
   ```

5. **Login as employee**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "emp001", "password": "temp123"}'
   ```

6. **Change password** (employee):
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
        -H "Authorization: Bearer <employee-token>" \
        -H "Content-Type: application/json" \
        -d '{
          "current_password": "temp123",
          "new_password": "newpass123",
          "confirm_password": "newpass123"
        }'
   ```

---

## 📝 Key Features

✅ **Multi-tenant architecture** - Complete company isolation
✅ **Role-based access control** - Admin vs Employee permissions
✅ **Secure authentication** - JWT tokens with role information
✅ **Password management** - Force password change on first login
✅ **Company isolation** - Each company only sees their own data
✅ **Soft deletes** - Preserve historical data
✅ **RESTful API** - Standard HTTP methods
✅ **Comprehensive documentation** - Swagger/OpenAPI at `/docs`

---

## 🔒 Security Features

- Passwords are hashed using bcrypt
- JWT tokens include role and company information
- Company data is isolated at the database query level
- Active status checks for both users and companies
- Force password change flag for new employees
- Bearer token authentication for all protected routes

---

## 📚 Next Steps

You can now extend this system with:

1. **Attendance module** - Track employee attendance
2. **Payroll module** - Manage employee salaries and payments
3. **Leave management** - Handle leave requests and approvals
4. **Performance reviews** - Track employee performance
5. **Email notifications** - Send credentials to new employees
6. **File uploads** - Handle employee documents and photos
7. **Reports** - Generate various HR reports
8. **Audit logs** - Track all changes for compliance

---

## 🐛 Troubleshooting

### Issue: "User.company" relationship error
**Solution**: Ensure all models are imported in `app/db/base.py`

### Issue: "force_password_change" column not found
**Solution**: Recreate the database tables (drop and create)

### Issue: Admin can't create employees
**Solution**: Check that the user's role is set to 'admin'

### Issue: Employees from different companies can see each other
**Solution**: Check that `company_id` filter is applied in queries

---

## 📞 Support

For questions or issues, refer to:
- API Documentation: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
- This guide: IMPLEMENTATION_GUIDE.md

---

**Congratulations! Your multi-tenant HRMS system is now ready! 🎉**

