# Employee API Documentation

## Overview

This documentation covers **only the APIs that employees can access**. Employees have limited access compared to admins - they can only view and manage their own data.

**Base URL:** `https://manahrms-backend.onrender.com/api/v1`

**Authentication:** Bearer Token (JWT)

All endpoints require the `Authorization` header:

```
Authorization: Bearer <access_token>
```

**Token Expiration:** 1 day (1440 minutes)

---

## Important Notes for Employees

⚠️ **Access Restrictions:**

- Employees can only view their **own** data
- Employees cannot see other employees' attendance, leave requests, or personal information
- Employees can only update/close tasks assigned to them
- Employees cannot create employees, projects, or departments
- Employees cannot approve leave requests

---

## Authentication

### How Do Employees Get Their Login Credentials?

**Step 1: Admin Creates Your Account**

- When an admin creates your employee account in the system, they will:
  - Set your employee details (name, email, department, etc.)
  - Provide an **initial password** (temporary password)
  - The system automatically generates a **username** based on your employee code

**Step 2: Receive Your Credentials**

- You will receive your login credentials from your admin/HR department:
  - **Username**: Usually based on your employee code (e.g., `emp00000001` or `emp00000001_1` if there's a conflict)
  - **Initial Password**: A temporary password set by the admin
  - **Email**: Your work email address

**Step 3: First Login**

- Use your username (or email) and the initial password to login
- **Important:** You should change your password immediately after first login for security

**Step 4: Change Password**

- After logging in, use the "Change Password" endpoint to set your own secure password

---

### 1. Login

Authenticate and get access token.

**Endpoint:** `POST /auth/login`

**Request Body:**

```json
{
  "username": "emp00000001",
  "password": "TempPassword123!"
}
```

**Note:** You can use either your **username** or **email** in the `username` field.

**Alternative using email:**

```json
{
  "username": "john.doe@techsolutions.com",
  "password": "TempPassword123!"
}
```

**Example Request:**

```bash
curl -X POST "https://manahrms-backend.onrender.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "emp00000001",
    "password": "TempPassword123!"
  }'
```

Authenticate and get access token.

**Endpoint:** `POST /auth/login`

**Request Body:**

```json
{
  "username": "emp00000001",
  "password": "TempPassword123!"
}
```

**Note:** You can use either your username or email in the `username` field.

**Alternative using email:**

```json
{
  "username": "john.doe@techsolutions.com",
  "password": "TempPassword123!"
}
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 5,
    "username": "emp00000001",
    "email": "john.doe@techsolutions.com",
    "full_name": "John Doe",
    "role": "employee",
    "company_id": 1,
    "is_active": true,
    "employee_id": 1
  }
}
```

**Error Responses:**

**401 Unauthorized** - Invalid credentials:

```json
{
  "detail": {
    "success": false,
    "message": "Incorrect username or password",
    "error_code": "INVALID_CREDENTIALS"
  }
}
```

**400 Bad Request** - Account inactive:

```json
{
  "detail": {
    "success": false,
    "message": "Inactive user account",
    "error_code": "USER_INACTIVE"
  }
}
```

**400 Bad Request** - Company inactive:

```json
{
  "detail": {
    "success": false,
    "message": "Company account is inactive",
    "error_code": "COMPANY_INACTIVE"
  }
}
```

**What to do if you forget your password:**

- Contact your admin/HR department to reset your password
- They can provide you with a new temporary password
- After receiving the new password, login and change it immediately

---

### 2. Get Current User

Get information about your account.

**Endpoint:** `GET /auth/me`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "id": 5,
  "username": "john.doe",
  "email": "john.doe@techsolutions.com",
  "full_name": "John Doe",
  "role": "employee",
  "company_id": 1,
  "is_active": true,
  "employee_id": 1
}
```

---

### 3. Change Password

Change your password.

**Endpoint:** `POST /auth/change-password`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response:** `200 OK`

```json
{
  "message": "Password changed successfully"
}
```

---

## Employee Information

### 1. Get My Employee Information

Get your own employee details.

**Endpoint:** `GET /employees/{employee_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Note:** You can only access your own employee ID (from `employee_id` in your user profile).

**Response:** `200 OK`

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "email": "john.doe@techsolutions.com",
  "phone": "+1234567890",
  "date_of_birth": "1990-05-15",
  "hire_date": "2024-01-01",
  "department_id": 1,
  "position": "Software Engineer",
  "employee_code": "EMP001",
  "is_active": true,
  "company_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### 2. Get Employees Dropdown

Get simplified list of active employees for dropdown selection (e.g., for task assignment).

**Endpoint:** `GET /employees/dropdown`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `search` (optional): Search by employee name or code
- `limit` (optional): Maximum results (default: 50, max: 100)

**Example Request:**

```
GET /employees/dropdown?search=john&limit=20
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "employee_code": "EMP001",
    "full_name": "John Doe"
  },
  {
    "id": 2,
    "employee_code": "EMP002",
    "full_name": "Jane Smith"
  }
]
```

**Note:** This shows all active employees in your company (for reference), but you cannot modify their data.

---

## Task Management

### 1. Get My Tasks (Simple Endpoint)

Get all tasks assigned to you - just send your token!

**Endpoint:** `GET /tasks/my-tasks`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status (`open`, `in_progress`, `closed`)
- `priority` (optional): Filter by priority (`low`, `medium`, `high`)

**Example Request:**

```
GET /tasks/my-tasks?page=1&page_size=20&status=open
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": 1,
      "title": "Implement user authentication",
      "description": "Add JWT-based authentication system",
      "assigned_to_employee_id": 1,
      "project_id": 1,
      "priority": "high",
      "status": "open",
      "due_date": "2024-02-01",
      "company_id": 1,
      "created_by_user_id": 1,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "project": {
        "id": 1,
        "name": "Website Redesign",
        "client": "ABC Corp"
      },
      "assigned_to_employee": {
        "id": 1,
        "employee_code": "EMP001",
        "full_name": "John Doe"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 10,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

**Note:** This endpoint automatically filters tasks by your employee ID from the token. No need to manually filter!

---

### 2. Query Tasks (Advanced)

Get paginated list of tasks with advanced filtering and sorting.

**Endpoint:** `POST /tasks/query`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body (To Get Only Your Tasks):**

```json
{
  "page": 1,
  "page_size": 20,
  "sort": [
    {
      "field": "due_date",
      "order": "asc"
    }
  ],
  "filter": [
    {
      "field": "assigned_to_employee_id",
      "operator": "eq",
      "value": 1
    },
    {
      "field": "status",
      "operator": "eq",
      "value": "open"
    }
  ]
}
```

**Request Body (To Get All Tasks in Company - Not Recommended):**

```json
{
  "page": 1,
  "page_size": 20,
  "sort": [
    {
      "field": "due_date",
      "order": "asc"
    }
  ],
  "filter": [
    {
      "field": "status",
      "operator": "eq",
      "value": "open"
    }
  ]
}
```

**Important Notes:**

⚠️ **Current Behavior:**

- The API currently returns **ALL tasks** in your company if you don't add a filter
- To see only **your tasks**, you **MUST** add a filter with your `assigned_to_employee_id`
- You can get your `employee_id` from the `/auth/me` endpoint (it's in the `employee_id` field)

**Recommended:** Always filter by your own `assigned_to_employee_id` to see only tasks assigned to you.

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": 1,
      "title": "Implement user authentication",
      "description": "Add JWT-based authentication system",
      "assigned_to_employee_id": 1,
      "project_id": 1,
      "priority": "high",
      "status": "open",
      "due_date": "2024-02-01",
      "company_id": 1,
      "created_by_user_id": 1,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "project": {
        "id": 1,
        "name": "Website Redesign",
        "client": "ABC Corp"
      },
      "assigned_to_employee": {
        "id": 1,
        "employee_code": "EMP001",
        "full_name": "John Doe"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 10,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

**Task Status Values:** `open`, `in_progress`, `closed`

**Task Priority Values:** `low`, `medium`, `high`

---

### 3. Get My Task by ID

Get detailed information about a specific task assigned to you.

**Endpoint:** `GET /tasks/{task_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Note:** You can only access tasks assigned to you. Accessing other tasks will return 404.

**Response:** `200 OK`

```json
{
  "id": 1,
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication system",
  "assigned_to_employee_id": 1,
  "project_id": 1,
  "priority": "high",
  "status": "open",
  "due_date": "2024-02-01",
  "company_id": 1,
  "created_by_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "project": {
    "id": 1,
    "name": "Website Redesign",
    "client": "ABC Corp"
  },
  "assigned_to_employee": {
    "id": 1,
    "employee_code": "EMP001",
    "full_name": "John Doe"
  }
}
```

---

### 4. Update My Task

Update a task assigned to you.

**Endpoint:** `PUT /tasks/{task_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Restrictions:**

- You can only update tasks assigned to you
- You **cannot** reassign tasks to other employees
- You **cannot** change the `assigned_to_employee_id` field

**Request Body:**

```json
{
  "title": "Implement user authentication - Updated",
  "description": "Add JWT-based authentication system with refresh tokens",
  "priority": "high",
  "status": "in_progress",
  "due_date": "2024-02-05"
}
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "title": "Implement user authentication - Updated",
  "description": "Add JWT-based authentication system with refresh tokens",
  "assigned_to_employee_id": 1,
  "project_id": 1,
  "priority": "high",
  "status": "in_progress",
  "due_date": "2024-02-05",
  "company_id": 1,
  "created_by_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "project": {
    "id": 1,
    "name": "Website Redesign",
    "client": "ABC Corp"
  },
  "assigned_to_employee": {
    "id": 1,
    "employee_code": "EMP001",
    "full_name": "John Doe"
  }
}
```

---

### 5. Close My Task

Mark a task assigned to you as closed.

**Endpoint:** `POST /tasks/{task_id}/close`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Note:** You can only close tasks assigned to you.

**Response:** `200 OK`

```json
{
  "id": 1,
  "title": "Implement user authentication - Updated",
  "description": "Add JWT-based authentication system with refresh tokens",
  "assigned_to_employee_id": 1,
  "project_id": 1,
  "priority": "high",
  "status": "closed",
  "due_date": "2024-02-05",
  "company_id": 1,
  "created_by_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z",
  "project": {
    "id": 1,
    "name": "Website Redesign",
    "client": "ABC Corp"
  },
  "assigned_to_employee": {
    "id": 1,
    "employee_code": "EMP001",
    "full_name": "John Doe"
  }
}
```

---

## Project Management

### 1. Get Projects

Get paginated list of projects in your company.

**Endpoint:** `POST /projects/query`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "page": 1,
  "page_size": 20,
  "sort": [
    {
      "field": "created_at",
      "order": "desc"
    }
  ],
  "filter": [
    {
      "field": "is_active",
      "operator": "eq",
      "value": true
    }
  ]
}
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": 1,
      "name": "Website Redesign",
      "client": "ABC Corp",
      "description": "Complete redesign of company website",
      "start_date": "2024-01-01",
      "end_date": "2024-06-30",
      "budget": 50000.0,
      "is_active": true,
      "company_id": 1,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 10,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

**Note:** You can view all projects in your company, but you cannot create, update, or delete them.

---

### 2. Get Projects Dropdown

Get simplified list of active projects for dropdown selection.

**Endpoint:** `GET /projects/dropdown`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `search` (optional): Search by project name or client
- `limit` (optional): Maximum results (default: 50, max: 100)

**Example Request:**

```
GET /projects/dropdown?search=website&limit=20
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "Website Redesign",
    "client": "ABC Corp"
  },
  {
    "id": 2,
    "name": "Mobile App Development",
    "client": "XYZ Inc"
  }
]
```

---

### 3. Get My Projects

Get all projects where you are the project lead.

**Endpoint:** `GET /projects/my-projects`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "Website Redesign",
    "client": "ABC Corp",
    "description": "Complete redesign of company website",
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "budget": 50000.0,
    "is_active": true,
    "company_id": 1,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 4. Get Project by ID

Get detailed information about a specific project.

**Endpoint:** `GET /projects/{project_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "name": "Website Redesign",
  "client": "ABC Corp",
  "description": "Complete redesign of company website",
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "budget": 50000.0,
  "is_active": true,
  "company_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "task_count": 15,
  "completed_task_count": 5,
  "open_task_count": 10
}
```

---

### 5. Get Project Tasks

Get all tasks for a specific project.

**Endpoint:** `GET /projects/{project_id}/tasks`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `status_filter` (optional): Filter by status (`open`, `in_progress`, `closed`)
- `priority_filter` (optional): Filter by priority (`low`, `medium`, `high`)

**Example Request:**

```
GET /projects/1/tasks?page=1&limit=20&status_filter=open
```

**Response:** `200 OK`

```json
{
  "total": 15,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": 1,
      "title": "Implement user authentication",
      "description": "Add JWT-based authentication system",
      "assigned_to_employee_id": 1,
      "project_id": 1,
      "priority": "high",
      "status": "open",
      "due_date": "2024-02-01",
      "company_id": 1,
      "created_by_user_id": 1,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "project": {
        "id": 1,
        "name": "Website Redesign",
        "client": "ABC Corp"
      },
      "assigned_to_employee": {
        "id": 1,
        "employee_code": "EMP001",
        "full_name": "John Doe"
      }
    }
  ]
}
```

**Note:** You can see all tasks in a project, but you can only update/close tasks assigned to you.

---

## Department Management

### 1. Get My Departments

Get paginated list of departments you have access to.

**Endpoint:** `POST /departments/query`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Note:** You can only see departments you have been granted access to by an admin.

**Request Body:**

```json
{
  "page": 1,
  "page_size": 20,
  "sort": [
    {
      "field": "name",
      "order": "asc"
    }
  ]
}
```

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": 1,
      "name": "Engineering",
      "description": "Software development and engineering",
      "is_active": true,
      "company_id": 1,
      "member_count": 15,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 2,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

---

### 2. Get Department by ID

Get detailed information about a specific department you have access to.

**Endpoint:** `GET /departments/{department_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Note:** You can only access departments you have been granted access to. Accessing other departments will return 403 Forbidden.

**Response:** `200 OK`

```json
{
  "id": 1,
  "name": "Engineering",
  "description": "Software development and engineering",
  "is_active": true,
  "company_id": 1,
  "member_count": 15,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## Attendance Management

### 1. Punch In

Record your punch in time for today.

**Endpoint:** `POST /attendance/punch-in`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Punched in successfully at 09:00:00",
  "attendance": {
    "id": 1,
    "employee_id": 1,
    "attendance_date": "2024-01-15",
    "punch_in_time": "2024-01-15T09:00:00Z",
    "punch_out_time": null,
    "work_duration_hours": null,
    "is_present": true,
    "is_checked_out": false,
    "company_id": 1,
    "created_at": "2024-01-15T09:00:00Z",
    "updated_at": "2024-01-15T09:00:00Z"
  }
}
```

---

### 2. Punch Out

Record your punch out time for today.

**Endpoint:** `POST /attendance/punch-out`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Punched out successfully at 18:00:00",
  "attendance": {
    "id": 1,
    "employee_id": 1,
    "attendance_date": "2024-01-15",
    "punch_in_time": "2024-01-15T09:00:00Z",
    "punch_out_time": "2024-01-15T18:00:00Z",
    "work_duration_hours": 9.0,
    "is_present": true,
    "is_checked_out": true,
    "company_id": 1,
    "created_at": "2024-01-15T09:00:00Z",
    "updated_at": "2024-01-15T18:00:00Z"
  },
  "work_duration_minutes": 540
}
```

---

### 3. Get Today's Attendance

Get today's attendance record.

**Endpoint:** `GET /attendance/today`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "employee_id": 1,
  "attendance_date": "2024-01-15",
  "punch_in_time": "2024-01-15T09:00:00Z",
  "punch_out_time": null,
  "work_duration_hours": null,
  "is_present": true,
  "is_checked_out": false,
  "company_id": 1,
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:00:00Z"
}
```

**Note:** Returns `null` if no attendance record exists for today.

---

### 4. Get My Attendance Calendar

Get your attendance calendar for a specific month.

**Endpoint:** `GET /attendance/calendar`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `year` (required): Year (e.g., 2024)
- `month` (required): Month (1-12)

**Example Request:**

```
GET /attendance/calendar?year=2024&month=1
```

**Response:** `200 OK`

```json
{
  "employee_id": 1,
  "month": 1,
  "year": 2024,
  "days": [
    {
      "date": "2024-01-01",
      "punch_in_time": "2024-01-01T09:00:00Z",
      "punch_out_time": "2024-01-01T18:00:00Z",
      "work_duration_minutes": 540,
      "is_present": true,
      "is_checked_out": true
    },
    {
      "date": "2024-01-02",
      "punch_in_time": null,
      "punch_out_time": null,
      "work_duration_minutes": null,
      "is_present": false,
      "is_checked_out": false
    }
  ],
  "total_present_days": 20,
  "total_work_hours": 180.0
}
```

**Note:** You can only see your own attendance. You cannot view other employees' attendance records.

---

## Leave Management

### 1. Apply for Leave

Apply for leave.

**Endpoint:** `POST /leaves/apply`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "leave_type_id": 1,
  "start_date": "2024-02-01",
  "end_date": "2024-02-05",
  "reason": "Family emergency"
}
```

**Response:** `201 Created`

```json
{
  "id": 1,
  "company_id": 1,
  "employee_id": 1,
  "leave_type_id": 1,
  "start_date": "2024-02-01",
  "end_date": "2024-02-05",
  "number_of_days": 5,
  "reason": "Family emergency",
  "status": "pending",
  "applied_date": "2024-01-15T10:30:00Z",
  "approved_by_user_id": null,
  "approved_date": null,
  "rejection_reason": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": null
}
```

---

### 2. Get My Leave Requests

Get your leave requests.

**Endpoint:** `GET /leaves/requests`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `status` (optional): Filter by status (`pending`, `approved`, `rejected`, `cancelled`)
- `start_date` (optional): Filter by start date
- `end_date` (optional): Filter by end date

**Note:** You can only see your own leave requests. The `employee_id` parameter is automatically set to your employee ID.

**Example Request:**

```
GET /leaves/requests?status=pending&start_date=2024-02-01&end_date=2024-02-28
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "company_id": 1,
    "employee_id": 1,
    "leave_type_id": 1,
    "start_date": "2024-02-01",
    "end_date": "2024-02-05",
    "number_of_days": 5,
    "reason": "Family emergency",
    "status": "pending",
    "applied_date": "2024-01-15T10:30:00Z",
    "approved_by_user_id": null,
    "approved_date": null,
    "rejection_reason": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "employee_name": "John Doe",
    "leave_type_name": "Sick Leave",
    "leave_type_code": "SL",
    "approved_by_name": null
  }
]
```

---

### 3. Cancel My Leave Request

Cancel your pending leave request.

**Endpoint:** `POST /leaves/requests/{leave_request_id}/cancel`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Note:** You can only cancel your own pending leave requests.

**Response:** `200 OK`

```json
{
  "id": 1,
  "company_id": 1,
  "employee_id": 1,
  "leave_type_id": 1,
  "start_date": "2024-02-01",
  "end_date": "2024-02-05",
  "number_of_days": 5,
  "reason": "Family emergency",
  "status": "cancelled",
  "applied_date": "2024-01-15T10:30:00Z",
  "approved_by_user_id": null,
  "approved_date": null,
  "rejection_reason": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T10:00:00Z",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": null
}
```

---

### 4. Get My Leave Balance

Get your leave balance.

**Endpoint:** `GET /leaves/balance`

**Permission:** Employee only

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `year` (optional): Year (defaults to current year)

**Note:** You can only see your own leave balance. The `employee_id` parameter is automatically set to your employee ID.

**Example Request:**

```
GET /leaves/balance?year=2024
```

**Response:** `200 OK`

```json
{
  "employee_id": 1,
  "employee_name": "John Doe",
  "year": 2024,
  "leave_balances": [
    {
      "id": 1,
      "company_id": 1,
      "employee_id": 1,
      "leave_type_id": 1,
      "year": 2024,
      "total_days": 10,
      "used_days": 3,
      "pending_days": 2,
      "available_days": 5,
      "carried_forward_days": 0,
      "leave_type_name": "Sick Leave",
      "leave_type_code": "SL",
      "employee_name": "John Doe"
    }
  ],
  "total_available_days": 5,
  "total_used_days": 3,
  "total_pending_days": 2
}
```

---

### 5. Get Leave Calendar

Get leave calendar for a date range (shows all approved and pending leaves in your company).

**Endpoint:** `GET /leaves/calendar`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `start_date` (required): Start date for calendar
- `end_date` (required): End date for calendar

**Example Request:**

```
GET /leaves/calendar?start_date=2024-02-01&end_date=2024-02-28
```

**Response:** `200 OK`

```json
{
  "start_date": "2024-02-01",
  "end_date": "2024-02-28",
  "leaves": [
    {
      "date": "2024-02-01",
      "employee_id": 1,
      "employee_name": "John Doe",
      "leave_type": "Sick Leave",
      "leave_type_code": "SL",
      "status": "approved",
      "number_of_days": 1
    },
    {
      "date": "2024-02-05",
      "employee_id": 2,
      "employee_name": "Jane Smith",
      "leave_type": "Casual Leave",
      "leave_type_code": "CL",
      "status": "pending",
      "number_of_days": 1
    }
  ]
}
```

**Note:** This shows all employees' leaves in your company (for planning purposes), but you can only manage your own leave requests.

---

### 6. Get Leave Types

Get all leave types available in your company.

**Endpoint:** `GET /leaves/types`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `active_only` (optional): Show only active leave types (default: true)

**Example Request:**

```
GET /leaves/types?active_only=true
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "company_id": 1,
    "name": "Sick Leave",
    "code": "SL",
    "description": "Leave for illness",
    "max_days_per_year": 10,
    "is_paid": true,
    "requires_approval": true,
    "can_carry_forward": false,
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

**Note:** You can view leave types, but you cannot create or update them (admin only).

---

## Dashboard APIs

### 1. Get Dashboard Overview

Get dashboard overview with statistics (filtered to your data).

**Endpoint:** `GET /dashboard/overview`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "overview": {
    "total_employees": 50,
    "total_tasks": 10,
    "total_projects": 10,
    "total_departments": 2
  },
  "task_stats": {
    "by_status": {
      "open": 3,
      "in_progress": 4,
      "closed": 3
    },
    "by_priority": {
      "low": 2,
      "medium": 5,
      "high": 3
    },
    "overdue_tasks": 1,
    "due_today": 1,
    "due_this_week": 3
  },
  "employee_stats": {
    "by_department": {
      "Engineering": 20,
      "Sales": 15
    },
    "active_employees": 48,
    "inactive_employees": 2
  },
  "attendance_stats": {
    "date": "2024-01-15",
    "total_employees": 50,
    "present_count": 45,
    "absent_count": 5,
    "present_percentage": 90.0,
    "absent_percentage": 10.0
  },
  "leave_stats": {
    "pending_requests": 2,
    "approved_this_month": 5,
    "rejected_this_month": 0,
    "total_leave_days_this_month": 10
  },
  "project_stats": {
    "active_projects": 8,
    "completed_projects": 2,
    "total_projects": 10
  },
  "recent_tasks": [
    {
      "id": 1,
      "title": "Implement user authentication",
      "status": "open",
      "priority": "high",
      "due_date": "2024-02-01",
      "assigned_to_employee": {
        "id": 1,
        "employee_code": "EMP001",
        "full_name": "John Doe"
      }
    }
  ],
  "upcoming_deadlines": [
    {
      "id": 1,
      "title": "Implement user authentication",
      "due_date": "2024-02-01",
      "priority": "high"
    }
  ],
  "recent_activities": [
    {
      "type": "task_created",
      "description": "Task 'Implement user authentication' was created",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Note:** Task statistics show only your tasks. Employee statistics show company-wide data (for reference).

---

### 2. Get Recent Tasks

Get your recent tasks.

**Endpoint:** `GET /dashboard/recent/tasks`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `limit` (optional): Number of recent tasks (default: 5, max: 20)

**Example Request:**

```
GET /dashboard/recent/tasks?limit=10
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "title": "Implement user authentication",
    "status": "open",
    "priority": "high",
    "due_date": "2024-02-01",
    "assigned_to_employee": {
      "id": 1,
      "employee_code": "EMP001",
      "full_name": "John Doe"
    }
  }
]
```

---

### 3. Get Upcoming Deadlines

Get your upcoming task deadlines.

**Endpoint:** `GET /dashboard/recent/deadlines`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `limit` (optional): Number of upcoming deadlines (default: 5, max: 20)

**Example Request:**

```
GET /dashboard/recent/deadlines?limit=10
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "title": "Implement user authentication",
    "due_date": "2024-02-01",
    "priority": "high"
  }
]
```

---

## Chat APIs

### 1. Get Users for Chat Dropdown

Get a list of users (User IDs) available for chat member selection.

**Endpoint:** `GET /chat/users/dropdown`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `search` (optional): Search by username, full name, or email
- `limit` (optional): Maximum results (default: 50, max: 100)

**Important:** Returns User IDs (from users table), NOT Employee IDs!

**Example Request:**

```
GET /chat/users/dropdown?search=john&limit=20
```

**Response:** `200 OK`

```json
[
  {
    "id": 7,
    "username": "john.doe",
    "full_name": "John Doe",
    "email": "john.doe@example.com",
    "role": "employee"
  }
]
```

---

### 2. Create Chat Room

Create a new individual or group chat room.

**Endpoint:** `POST /chat/rooms/create`

**Headers:**

```
Authorization: Bearer <access_token>
```

**For Individual Chat:**

```json
{
  "type": "individual",
  "member_user_ids": [7]
}
```

**For Group Chat:**

```json
{
  "type": "group",
  "name": "Project Team",
  "member_user_ids": [7, 8, 9]
}
```

**Important:** `member_user_ids` expects User IDs (from users table), NOT Employee IDs!

**Response:** `201 Created`

```json
{
  "id": 1,
  "company_id": 1,
  "name": null,
  "type": "individual",
  "created_by_user_id": 5,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "members": [
    {
      "id": 1,
      "user_id": 5,
      "role": "member",
      "joined_at": "2024-01-15T10:30:00Z",
      "user": {
        "id": 5,
        "username": "current.user",
        "full_name": "Current User",
        "email": "current@example.com"
      }
    },
    {
      "id": 2,
      "user_id": 7,
      "role": "member",
      "joined_at": "2024-01-15T10:30:00Z",
      "user": {
        "id": 7,
        "username": "john.doe",
        "full_name": "John Doe",
        "email": "john.doe@example.com"
      }
    }
  ],
  "last_message": null,
  "unread_count": 0
}
```

---

### 3. Get My Chat Rooms

Get all chat rooms you're part of (like WhatsApp chat list).

**Endpoint:** `GET /chat/rooms`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `room_type` (optional): Filter by room type (`individual` or `group`)

**Example Request:**

```
GET /chat/rooms?room_type=individual
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": null,
    "type": "individual",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:45:00Z",
    "last_message": {
      "id": 5,
      "chat_room_id": 1,
      "sender_user_id": 7,
      "message": "Hello! How are you?",
      "is_read": false,
      "created_at": "2024-01-15T11:45:00Z",
      "sender": {
        "id": 7,
        "username": "john.doe",
        "full_name": "John Doe",
        "email": "john.doe@example.com"
      }
    },
    "unread_count": 2,
    "member_count": 2,
    "other_user": {
      "id": 7,
      "username": "john.doe",
      "full_name": "John Doe",
      "email": "john.doe@example.com"
    }
  }
]
```

---

### 4. Get Chat Room Details

Get detailed information about a specific chat room you're part of.

**Endpoint:** `GET /chat/rooms/{room_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`

```json
{
  "id": 1,
  "company_id": 1,
  "name": null,
  "type": "individual",
  "created_by_user_id": 5,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "members": [
    {
      "id": 1,
      "user_id": 5,
      "role": "member",
      "joined_at": "2024-01-15T10:30:00Z",
      "user": {
        "id": 5,
        "username": "current.user",
        "full_name": "Current User",
        "email": "current@example.com"
      }
    },
    {
      "id": 2,
      "user_id": 7,
      "role": "member",
      "joined_at": "2024-01-15T10:30:00Z",
      "user": {
        "id": 7,
        "username": "john.doe",
        "full_name": "John Doe",
        "email": "john.doe@example.com"
      }
    }
  ],
  "last_message": {
    "id": 5,
    "chat_room_id": 1,
    "sender_user_id": 7,
    "message": "Hello! How are you?",
    "is_read": false,
    "created_at": "2024-01-15T11:45:00Z",
    "sender": {
      "id": 7,
      "username": "john.doe",
      "full_name": "John Doe",
      "email": "john.doe@example.com"
    }
  },
  "unread_count": 2
}
```

---

### 5. Get Chat Messages

Get messages in a chat room you're part of.

**Endpoint:** `GET /chat/rooms/{room_id}/messages`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- `limit` (optional): Number of messages (default: 50, max: 100)
- `offset` (optional): Offset for pagination (default: 0)

**Example Request:**

```
GET /chat/rooms/1/messages?limit=50&offset=0
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "chat_room_id": 1,
    "sender_user_id": 5,
    "message": "Hi there!",
    "is_read": true,
    "created_at": "2024-01-15T10:30:00Z",
    "sender": {
      "id": 5,
      "username": "current.user",
      "full_name": "Current User",
      "email": "current@example.com"
    }
  },
  {
    "id": 2,
    "chat_room_id": 1,
    "sender_user_id": 7,
    "message": "Hello! How are you?",
    "is_read": false,
    "created_at": "2024-01-15T10:35:00Z",
    "sender": {
      "id": 7,
      "username": "john.doe",
      "full_name": "John Doe",
      "email": "john.doe@example.com"
    }
  }
]
```

---

### 6. Send Message

Send a message in a chat room you're part of.

**Endpoint:** `POST /chat/rooms/{room_id}/messages`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "message": "Hello! This is my message."
}
```

**Constraints:** Message length: 1-5000 characters

**Response:** `201 Created`

```json
{
  "id": 4,
  "chat_room_id": 1,
  "sender_user_id": 5,
  "message": "Hello! This is my message.",
  "is_read": false,
  "created_at": "2024-01-15T12:00:00Z",
  "sender": {
    "id": 5,
    "username": "current.user",
    "full_name": "Current User",
    "email": "current@example.com"
  }
}
```

---

### 7. Add Member to Group

Add a member to a group chat (group admin only).

**Endpoint:** `POST /chat/rooms/{room_id}/members`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "user_id": 9
}
```

**Note:** Only group admins can add members. If you're not an admin, you'll get a 403 Forbidden error.

**Response:** `201 Created`

```json
{
  "id": 6,
  "user_id": 9,
  "role": "member",
  "joined_at": "2024-01-15T12:30:00Z",
  "user": {
    "id": 9,
    "username": "new.member",
    "full_name": "New Member",
    "email": "new.member@example.com"
  }
}
```

---

### 8. Remove Member from Group

Remove a member from a group chat.

**Endpoint:** `DELETE /chat/rooms/{room_id}/members/{user_id}`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Permissions:**

- Group admins can remove any member
- Members can remove themselves

**Response:** `200 OK`

```json
{
  "message": "Member removed from group successfully"
}
```

---

## AI Chat

### 1. Ask AI Chatbot

Ask the AI chatbot a question about company data in natural language.

**Endpoint:** `POST /ai-chat/ask`

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "question": "How many tasks are assigned to me?",
  "conversation_history": [
    {
      "role": "user",
      "content": "What is the total number of employees?"
    },
    {
      "role": "assistant",
      "content": "There are 50 employees in total."
    }
  ]
}
```

**Note:** `conversation_history` is optional and used for context in multi-turn conversations.

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "You have 10 tasks assigned to you. 3 are open, 4 are in progress, and 3 are closed.",
  "question": "How many tasks are assigned to me?"
}
```

---

## What Employees CANNOT Do

❌ **Cannot Create:**

- Employees
- Projects
- Departments
- Leave Types

❌ **Cannot Update:**

- Other employees' information
- Projects
- Departments
- Leave Types
- Tasks assigned to other employees
- Reassign tasks to other employees

❌ **Cannot Delete:**

- Employees
- Projects
- Departments

❌ **Cannot View:**

- Other employees' personal information (except in dropdowns)
- Other employees' attendance records
- Other employees' leave requests (except in calendar view)
- Other employees' leave balances
- All attendance statistics (company-wide)
- All leave requests (company-wide)

❌ **Cannot Approve:**

- Leave requests (only admins can approve/reject)

---

## Common Error Responses

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Not enough permissions"
}
```

**Or:**

```json
{
  "detail": {
    "success": false,
    "message": "Admin access required. Only company admins can perform this action.",
    "error_code": "ADMIN_ACCESS_REQUIRED"
  }
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

**Or:**

```json
{
  "detail": "Task not found"
}
```

**Note:** This may also mean you don't have access to the resource (e.g., trying to access another employee's task).

---

## Summary

As an employee, you can:

- ✅ View and manage your own tasks
- ✅ View projects and departments (with access)
- ✅ Punch in/out and view your own attendance
- ✅ Apply for leave and view your own leave balance
- ✅ Chat with other users
- ✅ Use AI chatbot
- ✅ View dashboard (filtered to your data)

You cannot:

- ❌ Create employees, projects, or departments
- ❌ View other employees' personal data
- ❌ Approve leave requests
- ❌ Access admin-only endpoints

---

## Testing Examples

### Login

```bash
curl -X POST "https://manahrms-backend.onrender.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "password": "YourPassword123!"
  }'
```

### Get My Tasks (Simple)

```bash
curl -X GET "https://manahrms-backend.onrender.com/api/v1/tasks/my-tasks?page=1&page_size=20&status=open" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get My Tasks (Advanced Query)

```bash
curl -X POST "https://manahrms-backend.onrender.com/api/v1/tasks/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 20,
    "filter": [
      {
        "field": "assigned_to_employee_id",
        "operator": "eq",
        "value": 1
      }
    ]
  }'
```

### Punch In

```bash
curl -X POST "https://manahrms-backend.onrender.com/api/v1/attendance/punch-in" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Apply for Leave

```bash
curl -X POST "https://manahrms-backend.onrender.com/api/v1/leaves/apply" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type_id": 1,
    "start_date": "2024-02-01",
    "end_date": "2024-02-05",
    "reason": "Family emergency"
  }'
```

---

## Support

For issues or questions, please contact your administrator or refer to the main API documentation.
