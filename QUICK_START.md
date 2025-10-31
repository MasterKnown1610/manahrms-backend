# 🚀 Quick Start Guide - HRMS Multi-Tenant System

## ⚡ Get Started in 5 Minutes!

### **Step 1: Setup Database** (1 minute)

```bash
# Run the database setup script
python create_tables.py

# Choose option 2: Drop and recreate all tables
# Type 'yes' when prompted
```

Expected output:
```
✅ All tables dropped successfully!
✅ Tables created successfully!
✅ Database recreated successfully!
```

---

### **Step 2: Start the Server** (30 seconds)

```bash
# Make the script executable (first time only)
chmod +x start_server.sh

# Start the server
./start_server.sh
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

### **Step 3: Test the API** (3 minutes)

#### **3.1 Register Your Company**

Open your browser or Postman and go to:
```
http://localhost:8000/docs
```

Or use curl:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register-company" \
     -H "Content-Type: application/json" \
     -d '{
       "company_name": "My Company",
       "company_email": "admin@mycompany.com",
       "company_phone": "+1234567890",
       "company_address": "123 Business St",
       "admin_full_name": "Admin User",
       "admin_email": "admin@mycompany.com",
       "admin_username": "admin",
       "admin_password": "admin123"
     }'
```

✅ **Success Response:**
```json
{
  "company": {
    "id": 1,
    "company_name": "My Company",
    "email": "admin@mycompany.com",
    ...
  },
  "admin_username": "admin",
  "message": "Company registered successfully! Admin can now login."
}
```

---

#### **3.2 Login as Admin**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "admin",
       "password": "admin123"
     }'
```

✅ **Success Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "company_id": 1,
    "username": "admin",
    "role": "admin",
    ...
  }
}
```

**📝 Copy the `access_token` - you'll need it!**

---

#### **3.3 Create a Department**

```bash
# Replace YOUR_TOKEN with the access_token from step 3.2
curl -X POST "http://localhost:8000/api/v1/departments" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Engineering",
       "description": "Software development team"
     }'
```

✅ **Success Response:**
```json
{
  "id": 1,
  "company_id": 1,
  "name": "Engineering",
  "description": "Software development team",
  "is_active": true,
  ...
}
```

---

#### **3.4 Add an Employee**

```bash
curl -X POST "http://localhost:8000/api/v1/employees" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "employee_code": "EMP001",
       "first_name": "John",
       "last_name": "Doe",
       "email": "john.doe@mycompany.com",
       "phone": "+1234567890",
       "position": "Software Engineer",
       "hire_date": "2025-01-15",
       "department_id": 1,
       "initial_password": "temp123"
     }'
```

✅ **Success Response:**
```json
{
  "employee": {
    "id": 1,
    "company_id": 1,
    "employee_code": "EMP001",
    "full_name": "John Doe",
    ...
  },
  "username": "emp001",
  "temp_password": "temp123",
  "message": "Employee created successfully. Please share credentials with the employee."
}
```

---

#### **3.5 Login as Employee**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "emp001",
       "password": "temp123"
     }'
```

✅ **Success Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "company_id": 1,
    "username": "emp001",
    "role": "employee",
    "force_password_change": true,  ← Employee must change password
    ...
  }
}
```

**📝 Copy the employee's `access_token`**

---

#### **3.6 Change Employee Password**

```bash
# Replace EMPLOYEE_TOKEN with the employee's access_token
curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
     -H "Authorization: Bearer EMPLOYEE_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "current_password": "temp123",
       "new_password": "myNewPass123",
       "confirm_password": "myNewPass123"
     }'
```

✅ **Success Response:**
```json
{
  "message": "Password changed successfully"
}
```

---

### **Step 4: Explore the API** (Optional)

Open your browser and visit:
```
http://localhost:8000/docs
```

This opens **Swagger UI** where you can:
- See all available endpoints
- Test endpoints interactively
- View request/response schemas
- Use "Authorize" button to add your token

---

## 📊 What You Just Built

```
✅ Multi-tenant HRMS system
✅ Company with admin user
✅ Department organization
✅ Employee with login credentials
✅ Role-based access control
✅ Password management
```

---

## 🎯 Common Use Cases

### **As Admin:**

**View all employees:**
```bash
curl -X GET "http://localhost:8000/api/v1/employees" \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Update employee:**
```bash
curl -X PUT "http://localhost:8000/api/v1/employees/1" \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "position": "Senior Software Engineer",
       "salary": 85000.00
     }'
```

**Get current user info:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

---

### **As Employee:**

**View my info:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer YOUR_EMPLOYEE_TOKEN"
```

**View all employees (read-only):**
```bash
curl -X GET "http://localhost:8000/api/v1/employees" \
     -H "Authorization: Bearer YOUR_EMPLOYEE_TOKEN"
```

**Change password:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
     -H "Authorization: Bearer YOUR_EMPLOYEE_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "current_password": "oldpass",
       "new_password": "newpass",
       "confirm_password": "newpass"
     }'
```

---

## 🐛 Troubleshooting

### **Issue: "Could not connect to database"**
**Solution:**
```bash
# Check if PostgreSQL is running
# Mac:
brew services list

# Linux:
sudo systemctl status postgresql

# Start if not running:
brew services start postgresql  # Mac
sudo systemctl start postgresql  # Linux
```

### **Issue: "Database 'HRMS' does not exist"**
**Solution:**
```bash
# Create the database
psql -U postgres
CREATE DATABASE "HRMS";
\q
```

### **Issue: "401 Unauthorized"**
**Solution:**
- Make sure you're using the correct token
- Token might be expired (login again)
- Check Authorization header format: `Bearer YOUR_TOKEN`

### **Issue: "403 Forbidden - Admin access required"**
**Solution:**
- This endpoint requires admin role
- Login with admin credentials
- Employees cannot access admin endpoints

---

## 📚 Next Steps

Now that you have the system running:

1. **Read the guides:**
   - `BEGINNER_GUIDE.md` - Understand how it works
   - `IMPLEMENTATION_GUIDE.md` - Technical details
   - `CHANGES_SUMMARY.md` - What was changed

2. **Explore the code:**
   - Models: `app/api/v1/models/`
   - Routes: `app/api/v1/routes/`
   - Services: `app/api/v1/services/`

3. **Test more features:**
   - Create multiple departments
   - Add more employees
   - Test employee login and password change
   - Test role-based access

4. **Build the frontend:**
   - Use the API endpoints
   - Implement login UI
   - Create admin dashboard
   - Build employee portal

---

## 🎉 Congratulations!

You now have a **fully functional multi-tenant HRMS system** with:
- ✅ Company isolation
- ✅ Role-based access
- ✅ Employee management
- ✅ Secure authentication
- ✅ Password management

**Ready for production deployment!** 🚀

---

## 💡 Pro Tips

1. **Use environment variables** for sensitive data (passwords, secret keys)
2. **Enable CORS** for frontend integration
3. **Add rate limiting** for production
4. **Setup logging** for debugging
5. **Write tests** for critical paths
6. **Document your API** (already done with Swagger!)

---

## 📞 Need Help?

- Check the `/docs` endpoint for API documentation
- Read `BEGINNER_GUIDE.md` for detailed explanations
- Review `IMPLEMENTATION_GUIDE.md` for technical details
- Look at the source code - it's well commented!

---

**Happy coding! 🎨**

