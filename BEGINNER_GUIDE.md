# 🎓 Beginner's Guide to HRMS Login & Data Flow

## 📖 Understanding the System (Simple Explanation)

Think of this HRMS system like an apartment building:
- Each **company** is a separate apartment
- Each apartment has an **admin** (owner/manager)
- Each apartment has **employees** (residents)
- People can only see what's in their own apartment!

---

## 🔄 Complete Data Flow Explained

### **Step 1: Company Registration**

**What happens:**
```
User fills registration form → Backend receives data → Creates 2 things:
  1. Company record (the apartment)
  2. Admin user (the manager)
```

**Real example:**
```
Input:
- Company: "Tech Innovations Inc"
- Admin Name: "Sarah Johnson"
- Admin Username: "sarah_admin"
- Admin Password: "SecurePass123"

What the system does:
1. Creates company in 'companies' table with ID=1
2. Creates admin user in 'users' table:
   - company_id = 1 (links to company)
   - role = "admin"
   - username = "sarah_admin"
   - password = [encrypted version of "SecurePass123"]

Result: Sarah can now login as the company admin!
```

---

### **Step 2: Admin Logs In**

**What happens:**
```
User enters username & password → Backend checks:
  1. Does username exist? ✓
  2. Is password correct? ✓
  3. Is user active? ✓
  4. Is company active? ✓
  
All good? → Create JWT token → Send back to user
```

**Real example:**
```
Input:
- Username: "sarah_admin"
- Password: "SecurePass123"

Backend process:
1. Find user with username "sarah_admin" in database
2. Compare password with stored hash
3. Check user.is_active = true
4. Check user.company.is_active = true
5. Create token with info:
   {
     "user_id": 1,
     "company_id": 1,
     "role": "admin",
     "username": "sarah_admin"
   }

Response:
{
  "access_token": "eyJhbG...[long token]",
  "user": {
    "id": 1,
    "username": "sarah_admin",
    "role": "admin",
    ...
  }
}

Frontend stores this token for future requests!
```

---

### **Step 3: Admin Adds Employee**

**What happens:**
```
Admin clicks "Add Employee" → Fills form → Backend:
  1. Checks admin has permission (role check)
  2. Creates employee record
  3. Creates login credentials for employee
  4. Returns employee info + username + password
```

**Real example:**
```
Admin (Sarah) wants to add employee John Smith

Input from admin:
- Employee Code: "EMP001"
- Name: "John Smith"
- Email: "john@techinnovations.com"
- Position: "Software Developer"
- Initial Password: "Welcome2024"

Backend process:
1. Check: Is Sarah an admin? YES (role = "admin")
2. Check: Does Sarah belong to company 1? YES
3. Create employee in 'employees' table:
   - company_id = 1 (Sarah's company)
   - employee_code = "EMP001"
   - first_name = "John"
   - last_name = "Smith"
   - email = "john@techinnovations.com"

4. Create user account for John in 'users' table:
   - company_id = 1 (same as Sarah's company)
   - username = "emp001" (auto-generated from employee_code)
   - role = "employee"
   - employee_id = [links to employee record]
   - password = [encrypted "Welcome2024"]
   - force_password_change = true (must change on first login)

Response to admin:
{
  "employee": {...employee details...},
  "username": "emp001",
  "temp_password": "Welcome2024",
  "message": "Employee created. Please share credentials."
}

Admin then tells John: "Your username is emp001, password is Welcome2024"
```

---

### **Step 4: Employee First Login**

**What happens:**
```
Employee enters credentials → Backend verifies → Login successful
But: force_password_change = true
Frontend shows: "Please change your password"
```

**Real example:**
```
John tries to login for the first time

Input:
- Username: "emp001"
- Password: "Welcome2024"

Backend process:
1. Find user "emp001" - FOUND
2. Check password - CORRECT
3. Check user.is_active - TRUE
4. Check company.is_active - TRUE
5. Create token with John's info:
   {
     "user_id": 2,
     "company_id": 1,
     "role": "employee",
     "username": "emp001"
   }

Response:
{
  "access_token": "eyJhbG...",
  "user": {
    "id": 2,
    "username": "emp001",
    "role": "employee",
    "force_password_change": true,  ← Frontend sees this!
    ...
  }
}

Frontend logic:
if (user.force_password_change === true) {
  showPasswordChangeDialog();
}
```

---

### **Step 5: Employee Changes Password**

**What happens:**
```
Employee submits new password → Backend:
  1. Verify current password is correct
  2. Update to new password
  3. Set force_password_change = false
  4. Save changes
```

**Real example:**
```
John wants to change from "Welcome2024" to "MySecurePass456"

Input (John sends with his token):
- current_password: "Welcome2024"
- new_password: "MySecurePass456"
- confirm_password: "MySecurePass456"

Backend process:
1. Token tells us: this is user_id=2 (John)
2. Get John's record from database
3. Check: Is "Welcome2024" his current password? YES
4. Update John's record:
   - hashed_password = [encrypt "MySecurePass456"]
   - force_password_change = false
5. Save to database

Response:
{
  "message": "Password changed successfully"
}

Now John can login normally with his new password!
```

---

### **Step 6: Daily Employee Login**

**What happens:**
```
Employee logs in with new password → Gets token → Uses token for all requests
```

**Real example:**
```
John logs in the next day

Input:
- Username: "emp001"
- Password: "MySecurePass456" (his new password)

Backend: [Same login process as Step 4]

Response:
{
  "access_token": "eyJhbG...",
  "user": {
    "force_password_change": false,  ← No prompt this time!
    ...
  }
}

John can now access employee portal normally!
```

---

## 🔐 How Token-Based Authentication Works

### Simple Explanation:

**Traditional sessions (like a ticket):**
```
You → Show ID at door → Get paper ticket → Keep ticket → Show ticket each time
Problem: Server must remember all tickets (uses memory)
```

**JWT tokens (like a stamp on your hand):**
```
You → Show ID → Get special stamp on hand → Show stamp each time
Server verifies stamp is real → No need to remember you!
```

### How it works in our system:

1. **Login:**
   ```
   User sends: username + password
   Server creates: JWT token (encrypted data)
   Token contains: user_id, company_id, role, expiry
   ```

2. **Making requests:**
   ```
   User sends: GET /api/v1/employees
   Headers: Authorization: Bearer eyJhbG...
   
   Server:
   - Decrypts token
   - Reads: user_id=2, company_id=1, role=employee
   - Checks: Is token expired? NO
   - Processes request using this info
   ```

3. **Company isolation:**
   ```
   When employee John (company_id=1) tries to get employees:
   
   Query: SELECT * FROM employees WHERE company_id = 1
   
   John only sees employees from company 1!
   Sarah from company 2 can't see John's data!
   ```

---

## 🛡️ Security Features Explained

### 1. **Password Hashing**
```
User's password: "MyPassword123"
Stored in DB: "$2b$12$vF9x.../Qy4T..." (encrypted)

Even if hacker steals database, they can't read passwords!
```

### 2. **Company Isolation**
```
Every query includes: WHERE company_id = current_user.company_id

Company A cannot see Company B's data - it's in the query!
```

### 3. **Role-Based Access**
```
Endpoint: POST /api/v1/employees (create employee)
Decorator: @require_admin

Backend checks:
if (user.role !== "admin") {
  return "403 Forbidden - Admin only"
}
```

### 4. **Force Password Change**
```
When admin creates employee:
- Set force_password_change = true

On login:
- Return this flag to frontend
- Frontend shows change password dialog

After change:
- Set force_password_change = false
- Normal access granted
```

---

## 📊 Database Relationships Explained

### **How tables connect:**

```
companies
   ↓ (has many)
departments
   ↓ (has many)
employees
   ↓ (has one)
users (for login)

Also:
companies
   ↓ (has many)
users (both admin and employee)
```

### **Real example:**

```
Company: "Tech Innovations" (id=1)
  ├── Admin User: "sarah_admin" (id=1, role=admin)
  ├── Department: "Engineering" (id=1)
  │     └── Employee: "John Smith" (id=1, employee_code=EMP001)
  │           └── User: "emp001" (id=2, role=employee, employee_id=1)
  └── Department: "HR" (id=2)
        └── Employee: "Jane Doe" (id=2, employee_code=EMP002)
              └── User: "emp002" (id=3, role=employee, employee_id=2)
```

---

## 🎯 Summary: Complete Request Flow

### **Example: Admin fetches all employees**

```
1. Frontend:
   Button click → Send request
   GET /api/v1/employees
   Header: Authorization: Bearer eyJhbG...

2. Backend receives request:
   Extract token from header

3. Dependencies (app/api/v1/dependencies.py):
   → get_current_user:
     - Decrypt token
     - Find user in database (id=1, role=admin, company_id=1)
     - Check user is active
     - Check company is active
     - Return user object
   
   → require_admin:
     - Check user.role === "admin" ✓
     - Allow access

4. Route handler (app/api/v1/routes/employees.py):
   → Call EmployeeService.get_all_employees
     - Pass company_id=1 from current_user

5. Service (app/api/v1/services/employee_service.py):
   → Query database:
     SELECT * FROM employees 
     WHERE company_id = 1  ← Only this company!
     LIMIT 100

6. Response back to frontend:
   [
     {"id": 1, "name": "John Smith", ...},
     {"id": 2, "name": "Jane Doe", ...}
   ]
```

---

## 🚀 Quick Start Checklist

- [ ] 1. Setup database (run `create_tables.py`)
- [ ] 2. Start server (`./start_server.sh`)
- [ ] 3. Register company (POST `/auth/register-company`)
- [ ] 4. Login as admin (POST `/auth/login`)
- [ ] 5. Create department (POST `/departments`)
- [ ] 6. Add employee (POST `/employees`)
- [ ] 7. Share credentials with employee
- [ ] 8. Employee logs in (POST `/auth/login`)
- [ ] 9. Employee changes password (POST `/auth/change-password`)
- [ ] 10. ✅ System ready!

---

## 💡 Key Concepts to Remember

1. **Multi-tenant** = Multiple companies, isolated data
2. **JWT Token** = Encrypted data that proves who you are
3. **Role-based** = Admin can do more than employees
4. **Company isolation** = Automatic in every query
5. **Force password change** = Security for new employees
6. **RESTful API** = Standard way to build web services

---

## 🎓 Learning Path

If you're new to this, learn in this order:

1. **HTTP basics** - GET, POST, PUT, DELETE
2. **REST APIs** - How web services work
3. **Authentication** - Username/password → token
4. **JWT tokens** - How they work
5. **Database relationships** - Foreign keys, joins
6. **Role-based access** - Admin vs user permissions

---

**Congratulations! You now understand how the HRMS system works! 🎉**

For more details, see:
- `IMPLEMENTATION_GUIDE.md` - Technical details
- `/docs` - Interactive API documentation
- Source code with comments

