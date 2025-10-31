# 🚀 Python Commands Guide - HRMS Backend

## 📍 Quick Reference Commands

### **1. Navigate to Project Directory**
```bash
cd /Users/aravindtrainings/Desktop/coding/Karthwini/hrms_saas_backend
```

---

### **2. Activate Virtual Environment**

**Option A: Using venv/bin/activate**
```bash
source venv/bin/activate
```

**Option B: Direct Python Path (No activation needed)**
```bash
# Just use: ./venv/bin/python for all commands
```

---

### **3. Test Database Connection**

```bash
# If venv is activated:
python test_connection.py

# Or without activation:
./venv/bin/python test_connection.py
```

**Expected Output:**
```
✅ CONNECTION SUCCESSFUL!
PostgreSQL Version: PostgreSQL 17.5...
```

---

### **4. Setup Database Tables**

```bash
# If venv is activated:
python create_tables.py

# Or without activation:
./venv/bin/python create_tables.py
```

**Choose option:**
- `1` - Create tables only (safe)
- `2` - Drop and recreate all tables (⚠️ deletes data)
- `3` - Exit

---

### **5. Start FastAPI Server**

**Option A: Using uvicorn directly**
```bash
# If venv is activated:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or without activation:
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Option B: Using the start script**
```bash
# Make executable (first time only):
chmod +x start_server.sh

# Run:
./start_server.sh
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Access API Docs:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API: http://localhost:8000/api/v1/

---

### **6. Run Tests (if you have tests)**

```bash
# If venv is activated:
pytest

# Or without activation:
./venv/bin/pytest
```

---

### **7. Check Python Version**

```bash
# If venv is activated:
python --version

# Or without activation:
./venv/bin/python --version
```

---

## 🔄 Complete Setup & Run Workflow

### **First Time Setup:**

```bash
# 1. Navigate to project
cd /Users/aravindtrainings/Desktop/coding/Karthwini/hrms_saas_backend

# 2. Test database connection
./venv/bin/python test_connection.py

# 3. Create database tables
./venv/bin/python create_tables.py
# Choose option 2 (drop and recreate)

# 4. Start the server
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### **Daily Development Workflow:**

```bash
# 1. Navigate to project
cd /Users/aravindtrainings/Desktop/coding/Karthwini/hrms_saas_backend

# 2. Activate venv (optional)
source venv/bin/activate

# 3. Start server (with auto-reload for development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Server will auto-reload on code changes!
```

---

## 🛠️ Useful Development Commands

### **Check Installed Packages**
```bash
./venv/bin/pip list
```

### **Install New Package**
```bash
./venv/bin/pip install package-name
```

### **Update Requirements**
```bash
./venv/bin/pip freeze > requirements.txt
```

### **Check for Linter Errors**
```bash
# If you have flake8 installed:
./venv/bin/flake8 app/

# If you have black installed (format code):
./venv/bin/black app/
```

---

## 🔍 Debugging Commands

### **Run Python REPL with App Context**
```bash
./venv/bin/python
```
Then in Python:
```python
from app.core.config import settings
print(settings.DATABASE_URL)

from app.db.session import engine
with engine.connect() as conn:
    print("Connected!")
```

### **Check Environment Variables**
```bash
# View .env file
cat .env

# Or check if DATABASE_URL is set:
./venv/bin/python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

---

## 📦 Production Commands

### **Start Server (Production Mode)**
```bash
# No auto-reload, better for production
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### **Start with Logging**
```bash
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

---

## 🌐 Test API Endpoints

Once server is running, test with curl:

### **Test Connection**
```bash
curl http://localhost:8000/api/v1/
```

### **Register Company**
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

### **Login**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "password123"}'
```

---

## ⚠️ Troubleshooting

### **If "command not found" error:**
```bash
# Always use full path:
./venv/bin/python <command>
```

### **If connection fails:**
```bash
# Check .env file exists:
cat .env

# Verify DATABASE_URL:
./venv/bin/python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### **If port 8000 is busy:**
```bash
# Use different port:
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### **If import errors:**
```bash
# Make sure you're in project directory:
pwd
# Should show: .../hrms_saas_backend

# Install dependencies:
./venv/bin/pip install -r requirements.txt
```

---

## 📝 Quick Command Reference

| Task | Command |
|------|---------|
| **Test DB** | `./venv/bin/python test_connection.py` |
| **Setup DB** | `./venv/bin/python create_tables.py` |
| **Start Server** | `./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| **Run Tests** | `./venv/bin/pytest` |
| **Check Config** | `./venv/bin/python -c "from app.core.config import settings; print(settings.DATABASE_URL)"` |
| **Install Package** | `./venv/bin/pip install package-name` |

---

## 🎯 Most Common Commands

**For daily development, you'll mostly use:**

```bash
# 1. Start server
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Test connection (if issues)
./venv/bin/python test_connection.py

# 3. Create tables (after schema changes)
./venv/bin/python create_tables.py
```

---

**Happy coding! 🚀**

