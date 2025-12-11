# Complete HRMS API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Employee Management](#employee-management)
4. [Task Management](#task-management)
5. [Project Management](#project-management)
6. [Department Management](#department-management)
7. [Attendance Management](#attendance-management)
8. [Leave Management](#leave-management)
9. [Dashboard APIs](#dashboard-apis)
10. [Chat APIs](#chat-apis)
11. [AI Chat](#ai-chat)
12. [Common Patterns](#common-patterns)

---

## Overview

**Base URL:** `http://localhost:8000/api/v1`

**API Version:** v1

**Authentication:** Bearer Token (JWT)

All authenticated endpoints require the `Authorization` header:
```
Authorization: Bearer <access_token>
```

**Token Expiration:** 1 day (1440 minutes)

---

## Authentication

### 1. Register Company

Register a new company and create the admin user.

**Endpoint:** `POST /auth/register-company`

**Request Body:**
```json
{
  "company_name": "Tech Solutions Inc",
  "admin_username": "admin",
  "admin_email": "admin@techsolutions.com",
  "admin_password": "SecurePassword123!",
  "admin_full_name": "Admin User"
}
```

**Response:** `201 Created`
```json
{
  "company": {
    "id": 1,
    "name": "Tech Solutions Inc",
    "created_at": "2024-01-15T10:00:00Z"
  },
  "admin_username": "admin",
  "message": "Company registered successfully! Admin can now login."
}
```

---

### 2. Login

Authenticate user and get access token.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "username": "admin",
  "password": "SecurePassword123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@techsolutions.com",
    "full_name": "Admin User",
    "role": "admin",
    "company_id": 1,
    "is_active": true
  }
}
```

---

### 3. Get Current User

Get information about the currently authenticated user.

**Endpoint:** `GET /auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@techsolutions.com",
  "full_name": "Admin User",
  "role": "admin",
  "company_id": 1,
  "is_active": true
}
```

---

### 4. Change Password

Change the current user's password.

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

## Employee Management

### 1. Create Employee

Create a new employee and generate login credentials.

**Endpoint:** `POST /employees/create`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@techsolutions.com",
  "phone": "+1234567890",
  "date_of_birth": "1990-05-15",
  "hire_date": "2024-01-01",
  "department_id": 1,
  "position": "Software Engineer",
  "employee_code": "EMP001",
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "employee": {
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
  },
  "username": "john.doe",
  "temp_password": "TempPass123!",
  "message": "Employee created successfully. Please share credentials with the employee."
}
```

---

### 2. Query Employees

Get paginated list of employees with filtering and sorting.

**Endpoint:** `POST /employees/query`

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
    },
    {
      "field": "department_id",
      "operator": "eq",
      "value": 1
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
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 50,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false
  }
}
```

---

### 3. Get Employees Dropdown

Get simplified list of active employees for dropdown selection.

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

---

### 4. Get Employee by ID

Get detailed information about a specific employee.

**Endpoint:** `GET /employees/{employee_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

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

### 5. Update Employee

Update employee information.

**Endpoint:** `PUT /employees/{employee_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe Updated",
  "phone": "+1234567891",
  "position": "Senior Software Engineer",
  "is_active": true
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe Updated",
  "full_name": "John Doe Updated",
  "email": "john.doe@techsolutions.com",
  "phone": "+1234567891",
  "date_of_birth": "1990-05-15",
  "hire_date": "2024-01-01",
  "department_id": 1,
  "position": "Senior Software Engineer",
  "employee_code": "EMP001",
  "is_active": true,
  "company_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

---

### 6. Delete Employee

Soft delete an employee (deactivates and allows email reuse).

**Endpoint:** `DELETE /employees/{employee_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "message": "Employee 1 has been deleted successfully. The email can now be reused in another company."
}
```

---

## Task Management

### 1. Create Task

Create a new task.

**Endpoint:** `POST /tasks/create`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication system",
  "assigned_to_employee_id": 1,
  "project_id": 1,
  "priority": "high",
  "status": "open",
  "due_date": "2024-02-01"
}
```

**Response:** `201 Created`
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

**Task Status Values:** `open`, `in_progress`, `closed`

**Task Priority Values:** `low`, `medium`, `high`

---

### 2. Query Tasks

Get paginated list of tasks with filtering and sorting.

**Endpoint:** `POST /tasks/query`

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
      "field": "due_date",
      "order": "asc"
    }
  ],
  "filter": [
    {
      "field": "status",
      "operator": "eq",
      "value": "open"
    },
    {
      "field": "assigned_to_employee_id",
      "operator": "eq",
      "value": 1
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
    "total_items": 25,
    "total_pages": 2,
    "has_next": true,
    "has_previous": false
  }
}
```

---

### 3. Get Task by ID

Get detailed information about a specific task.

**Endpoint:** `GET /tasks/{task_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

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

### 4. Update Task

Update task information.

**Endpoint:** `PUT /tasks/{task_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Note:** 
- Admins can update any task
- Employees can only update their own assigned tasks (cannot reassign)

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

### 5. Close Task

Mark a task as closed.

**Endpoint:** `POST /tasks/{task_id}/close`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Note:**
- Admins can close any task
- Employees can only close their own assigned tasks

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

### 1. Create Project

Create a new project.

**Endpoint:** `POST /projects/create`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Website Redesign",
  "client": "ABC Corp",
  "description": "Complete redesign of company website",
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "budget": 50000.00,
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Website Redesign",
  "client": "ABC Corp",
  "description": "Complete redesign of company website",
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "budget": 50000.00,
  "is_active": true,
  "company_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### 2. Query Projects

Get paginated list of projects with filtering and sorting.

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
      "budget": 50000.00,
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

---

### 3. Get Projects Dropdown

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

### 4. Get My Projects

Get all projects where the current user is the project lead.

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
    "budget": 50000.00,
    "is_active": true,
    "company_id": 1,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 5. Get Project by ID

Get detailed information about a specific project with task statistics.

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
  "budget": 50000.00,
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

### 6. Get Project Tasks

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

---

### 7. Update Project

Update project information.

**Endpoint:** `PUT /projects/{project_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Website Redesign - Updated",
  "description": "Complete redesign with new features",
  "end_date": "2024-07-30",
  "budget": 60000.00
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Website Redesign - Updated",
  "client": "ABC Corp",
  "description": "Complete redesign with new features",
  "start_date": "2024-01-01",
  "end_date": "2024-07-30",
  "budget": 60000.00,
  "is_active": true,
  "company_id": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

---

### 8. Deactivate Project

Soft delete a project.

**Endpoint:** `DELETE /projects/{project_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "message": "Project 'Website Redesign' has been deactivated successfully"
}
```

---

## Department Management

### 1. Create Department

Create a new department.

**Endpoint:** `POST /departments/create`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Engineering",
  "description": "Software development and engineering"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Engineering",
  "description": "Software development and engineering",
  "is_active": true,
  "company_id": 1,
  "member_count": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### 2. Query Departments

Get paginated list of departments.

**Endpoint:** `POST /departments/query`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Note:** 
- Admins see all departments in their company
- Employees see only departments they have access to

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
    "total_items": 5,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

---

### 3. Get Department by ID

Get detailed information about a specific department.

**Endpoint:** `GET /departments/{department_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

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

### 4. Update Department

Update department information.

**Endpoint:** `PUT /departments/{department_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Engineering - Updated",
  "description": "Software development, engineering, and DevOps"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Engineering - Updated",
  "description": "Software development, engineering, and DevOps",
  "is_active": true,
  "company_id": 1,
  "member_count": 15,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

---

### 5. Deactivate Department

Deactivate a department.

**Endpoint:** `DELETE /departments/{department_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "message": "Department 'Engineering' has been deactivated successfully"
}
```

---

### 6. Grant Department Access

Grant a user access to a department.

**Endpoint:** `POST /departments/access/grant`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "department_id": 1,
  "user_id": 5
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "department_id": 1,
  "user_id": 5,
  "granted_by_user_id": 1,
  "granted_at": "2024-01-15T10:30:00Z"
}
```

---

### 7. Revoke Department Access

Revoke a user's access to a department.

**Endpoint:** `POST /departments/access/revoke`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "department_id": 1,
  "user_id": 5
}
```

**Response:** `200 OK`
```json
{
  "message": "Department access has been revoked successfully"
}
```

---

### 8. Get Department Users

Get all users who have access to a specific department.

**Endpoint:** `GET /departments/{department_id}/users`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "department_id": 1,
  "department_name": "Engineering",
  "users": [
    {
      "user_id": 5,
      "username": "john.doe",
      "full_name": "John Doe",
      "email": "john.doe@techsolutions.com",
      "granted_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### 9. Get User Departments

Get all departments a specific user has access to.

**Endpoint:** `GET /departments/users/{user_id}/departments`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
[
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
]
```

---

## Attendance Management

### 1. Punch In

Record employee punch in time for today.

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

Record employee punch out time for today.

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

Get today's attendance record for the current employee.

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

### 4. Get Attendance Calendar

Get attendance calendar for a specific month.

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

---

### 5. Get Attendance Statistics

Get attendance statistics for a specific date.

**Endpoint:** `GET /attendance/stats`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `target_date` (optional): Date to get stats for (defaults to today)

**Example Request:**
```
GET /attendance/stats?target_date=2024-01-15
```

**Response:** `200 OK`
```json
{
  "date": "2024-01-15",
  "total_employees": 50,
  "present_count": 45,
  "absent_count": 5,
  "present_percentage": 90.0,
  "absent_percentage": 10.0
}
```

---

### 6. Query Attendance Records

Get paginated list of attendance records with filtering and sorting.

**Endpoint:** `POST /attendance/query`

**Permission:** Admin only

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
      "field": "attendance_date",
      "order": "desc"
    }
  ],
  "filter": [
    {
      "field": "is_present",
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
      "employee_id": 1,
      "employee_name": "John Doe",
      "attendance_date": "2024-01-15",
      "punch_in_time": "2024-01-15T09:00:00Z",
      "punch_out_time": "2024-01-15T18:00:00Z",
      "work_duration_minutes": 540,
      "is_present": true,
      "is_checked_out": true
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

---

### 7. Get Employee Attendance Calendar

Get attendance calendar for a specific employee (admin only).

**Endpoint:** `GET /attendance/employee/{employee_id}/calendar`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `year` (required): Year (e.g., 2024)
- `month` (required): Month (1-12)

**Example Request:**
```
GET /attendance/employee/1/calendar?year=2024&month=1
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
    }
  ],
  "total_present_days": 20,
  "total_work_hours": 180.0
}
```

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

### 2. Get Leave Requests

Get leave requests with optional filtering.

**Endpoint:** `GET /leaves/requests`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `employee_id` (optional): Filter by employee ID
- `status` (optional): Filter by status (`pending`, `approved`, `rejected`, `cancelled`)
- `start_date` (optional): Filter by start date
- `end_date` (optional): Filter by end date

**Note:**
- Employees see only their own requests
- Admins see all requests in their company

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

### 3. Approve/Reject Leave Request

Approve or reject a leave request.

**Endpoint:** `POST /leaves/requests/{leave_request_id}/approve`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "status": "approved"
}
```

**Or for rejection:**
```json
{
  "status": "rejected",
  "rejection_reason": "Insufficient coverage"
}
```

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
  "status": "approved",
  "applied_date": "2024-01-15T10:30:00Z",
  "approved_by_user_id": 1,
  "approved_date": "2024-01-16T09:00:00Z",
  "rejection_reason": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T09:00:00Z",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": "Admin User"
}
```

---

### 4. Cancel Leave Request

Cancel a pending leave request.

**Endpoint:** `POST /leaves/requests/{leave_request_id}/cancel`

**Permission:** Employee only (can cancel own requests)

**Headers:**
```
Authorization: Bearer <access_token>
```

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

### 5. Get Leave Balance

Get leave balance for an employee.

**Endpoint:** `GET /leaves/balance`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `employee_id` (optional): Employee ID (admin only, employees see own balance)
- `year` (optional): Year (defaults to current year)

**Example Request:**
```
GET /leaves/balance?employee_id=1&year=2024
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

### 6. Get Leave Calendar

Get leave calendar for a date range.

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
    }
  ]
}
```

---

### 7. Create Leave Type

Create a new leave type.

**Endpoint:** `POST /leaves/types`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Sick Leave",
  "code": "SL",
  "description": "Leave for illness",
  "max_days_per_year": 10,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": false
}
```

**Response:** `201 Created`
```json
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
```

---

### 8. Get Leave Types

Get all leave types for the company.

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

---

### 9. Update Leave Type

Update a leave type.

**Endpoint:** `PUT /leaves/types/{leave_type_id}`

**Permission:** Admin only

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Sick Leave - Updated",
  "max_days_per_year": 12,
  "description": "Leave for illness and medical appointments"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "company_id": 1,
  "name": "Sick Leave - Updated",
  "code": "SL",
  "description": "Leave for illness and medical appointments",
  "max_days_per_year": 12,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": false,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

---

## Dashboard APIs

### 1. Get Dashboard Overview

Get complete dashboard overview with all statistics.

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
    "total_tasks": 100,
    "total_projects": 10,
    "total_departments": 5
  },
  "task_stats": {
    "by_status": {
      "open": 30,
      "in_progress": 40,
      "closed": 30
    },
    "by_priority": {
      "low": 20,
      "medium": 50,
      "high": 30
    },
    "overdue_tasks": 5,
    "due_today": 3,
    "due_this_week": 10
  },
  "employee_stats": {
    "by_department": {
      "Engineering": 20,
      "Sales": 15,
      "Marketing": 10,
      "HR": 5
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
    "pending_requests": 5,
    "approved_this_month": 20,
    "rejected_this_month": 2,
    "total_leave_days_this_month": 50
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

---

### 2. Get Overview Statistics

Get overview statistics only.

**Endpoint:** `GET /dashboard/stats/overview`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "total_employees": 50,
  "total_tasks": 100,
  "total_projects": 10,
  "total_departments": 5
}
```

---

### 3. Get Task Statistics

Get task statistics breakdown.

**Endpoint:** `GET /dashboard/stats/tasks`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "by_status": {
    "open": 30,
    "in_progress": 40,
    "closed": 30
  },
  "by_priority": {
    "low": 20,
    "medium": 50,
    "high": 30
  },
  "overdue_tasks": 5,
  "due_today": 3,
  "due_this_week": 10
}
```

---

### 4. Get Employee Statistics

Get employee statistics.

**Endpoint:** `GET /dashboard/stats/employees`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "by_department": {
    "Engineering": 20,
    "Sales": 15,
    "Marketing": 10,
    "HR": 5
  },
  "active_employees": 48,
  "inactive_employees": 2
}
```

---

### 5. Get Attendance Statistics

Get attendance statistics for a specific date.

**Endpoint:** `GET /dashboard/stats/attendance`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `target_date` (optional): Target date (defaults to today)

**Example Request:**
```
GET /dashboard/stats/attendance?target_date=2024-01-15
```

**Response:** `200 OK`
```json
{
  "date": "2024-01-15",
  "total_employees": 50,
  "present_count": 45,
  "absent_count": 5,
  "present_percentage": 90.0,
  "absent_percentage": 10.0
}
```

---

### 6. Get Leave Statistics

Get leave statistics.

**Endpoint:** `GET /dashboard/stats/leaves`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "pending_requests": 5,
  "approved_this_month": 20,
  "rejected_this_month": 2,
  "total_leave_days_this_month": 50
}
```

---

### 7. Get Project Statistics

Get project statistics.

**Endpoint:** `GET /dashboard/stats/projects`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "active_projects": 8,
  "completed_projects": 2,
  "total_projects": 10
}
```

---

### 8. Get Recent Tasks

Get recent tasks.

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

### 9. Get Upcoming Deadlines

Get upcoming task deadlines.

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

### 10. Get Recent Activities

Get recent activities across different entities.

**Endpoint:** `GET /dashboard/recent/activities`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `limit` (optional): Number of recent activities (default: 10, max: 50)

**Example Request:**
```
GET /dashboard/recent/activities?limit=20
```

**Response:** `200 OK`
```json
[
  {
    "type": "task_created",
    "description": "Task 'Implement user authentication' was created",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  {
    "type": "employee_created",
    "description": "Employee 'John Doe' was created",
    "timestamp": "2024-01-15T09:00:00Z"
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
  },
  {
    "id": 8,
    "username": "jane.smith",
    "full_name": "Jane Smith",
    "email": "jane.smith@example.com",
    "role": "admin"
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

Get all chat rooms for the current user (like WhatsApp chat list).

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

Get detailed information about a specific chat room.

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

Get messages in a chat room with pagination.

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

**Note:** Messages are returned in chronological order (oldest first).

---

### 6. Send Message

Send a message in a chat room.

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

Add a member to a group chat (admin only).

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
  "question": "How many employees are in the Engineering department?",
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
  "message": "There are 20 employees in the Engineering department.",
  "question": "How many employees are in the Engineering department?"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "AI service is not configured. Please contact your administrator to set up the OpenAI API key.",
  "question": "How many employees are in the Engineering department?"
}
```

---

## Common Patterns

### Pagination

Most list endpoints use a POST method with a pagination request body:

**Request:**
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

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

### Filter Operators

- `eq` - Equals
- `ne` - Not equals
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `contains` - Contains (for strings)
- `in` - In array
- `not_in` - Not in array
- `is_null` - Is null
- `is_not_null` - Is not null

### Sort Order

- `asc` - Ascending
- `desc` - Descending

### Error Responses

**400 Bad Request:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not enough permissions"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Authentication Flow

1. **Register Company** → Creates company and admin user
2. **Login** → Get access token
3. **Use Token** → Include in `Authorization: Bearer <token>` header for all authenticated requests
4. **Token Expires** → Login again to get new token (expires after 1 day)

---

## Permissions

### Admin
- Can perform all operations
- Can manage employees, projects, departments, tasks
- Can approve/reject leave requests
- Can view all company data

### Employee
- Can view own data
- Can update own assigned tasks (cannot reassign)
- Can close own assigned tasks
- Can apply for leave
- Can view own attendance
- Can punch in/out
- Can chat with other users
- Cannot create employees, projects, departments
- Cannot approve leave requests

---

## Notes

1. **Company Isolation:** All operations are scoped to the user's company
2. **Soft Deletes:** Employees and projects are soft-deleted (deactivated), not permanently removed
3. **User IDs vs Employee IDs:** 
   - Chat APIs use User IDs (from `users` table)
   - Task assignment uses Employee IDs (from `employees` table)
4. **Date Formats:** All dates use ISO 8601 format (YYYY-MM-DD)
5. **DateTime Formats:** All timestamps use ISO 8601 format with timezone (YYYY-MM-DDTHH:MM:SSZ)

---

## Testing

### Base URL
```
http://localhost:8000/api/v1
```

### Example cURL Commands

**Login:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "SecurePassword123!"
  }'
```

**Get Employees:**
```bash
curl -X POST "http://localhost:8000/api/v1/employees/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 20
  }'
```

**Create Task:**
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication system",
    "assigned_to_employee_id": 1,
    "project_id": 1,
    "priority": "high",
    "status": "open",
    "due_date": "2024-02-01"
  }'
```

---

## Support

For issues or questions, please refer to the API documentation at `/docs` (Swagger UI) or `/redoc` (ReDoc) when the server is running.

