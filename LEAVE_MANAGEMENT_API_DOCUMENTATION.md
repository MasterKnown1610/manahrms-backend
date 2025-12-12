# Leave Management API Documentation

Complete API documentation for Leave Management system covering both Admin and Employee endpoints.

**Base URL:** `/api/v1/leaves`

**Authentication:** All endpoints require Bearer token authentication.

---

## Table of Contents

1. [Employee Endpoints](#employee-endpoints)
2. [Admin Endpoints](#admin-endpoints)
3. [Common Endpoints](#common-endpoints)
4. [Data Models](#data-models)
5. [Error Codes](#error-codes)

---

## Employee Endpoints

### 1. Apply for Leave

**Endpoint:** `POST /leaves/apply`

**Description:** Employees can apply for leave by providing leave type, dates, and optional reason.

**Access:** Employee only (must be associated with an employee)

**Request Body:**

```json
{
  "leave_type_id": 1,
  "start_date": "2024-01-15",
  "end_date": "2024-01-17",
  "reason": "Personal reasons" // Optional
}
```

**Request Schema:**

- `leave_type_id` (integer, required): ID of the leave type
- `start_date` (date, required): Format: `YYYY-MM-DD`
- `end_date` (date, required): Format: `YYYY-MM-DD`, must be >= start_date
- `reason` (string, optional): Reason for leave

**Response:** `201 Created`

```json
{
  "id": 123,
  "company_id": 1,
  "employee_id": 5,
  "leave_type_id": 1,
  "start_date": "2024-01-15",
  "end_date": "2024-01-17",
  "number_of_days": 3,
  "reason": "Personal reasons",
  "status": "pending",
  "applied_date": "2024-01-10T10:30:00",
  "approved_by_user_id": null,
  "approved_date": null,
  "rejection_reason": null,
  "created_at": "2024-01-10T10:30:00",
  "updated_at": "2024-01-10T10:30:00",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": null
}
```

**Example:**

```bash
curl -X POST "https://api.example.com/api/v1/leaves/apply" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type_id": 1,
    "start_date": "2024-01-15",
    "end_date": "2024-01-17",
    "reason": "Family emergency"
  }'
```

---

### 2. Get My Leave Requests

**Endpoint:** `GET /leaves/requests`

**Description:** Get leave requests. Employees see only their own requests.

**Access:** Employee (sees own requests), Admin (sees all company requests)

**Query Parameters:**

- `employee_id` (integer, optional): Filter by employee ID (Admin only)
- `status` (string, optional): Filter by status (`pending`, `approved`, `rejected`, `cancelled`)
- `start_date` (date, optional): Filter by start date (format: `YYYY-MM-DD`)
- `end_date` (date, optional): Filter by end date (format: `YYYY-MM-DD`)

**Response:** `200 OK`

```json
[
  {
    "id": 123,
    "company_id": 1,
    "employee_id": 5,
    "leave_type_id": 1,
    "start_date": "2024-01-15",
    "end_date": "2024-01-17",
    "number_of_days": 3,
    "reason": "Personal reasons",
    "status": "pending",
    "applied_date": "2024-01-10T10:30:00",
    "approved_by_user_id": null,
    "approved_date": null,
    "rejection_reason": null,
    "created_at": "2024-01-10T10:30:00",
    "updated_at": "2024-01-10T10:30:00",
    "employee_name": "John Doe",
    "leave_type_name": "Sick Leave",
    "leave_type_code": "SL",
    "approved_by_name": null
  }
]
```

**Example:**

```bash
# Get all my leave requests
curl -X GET "https://api.example.com/api/v1/leaves/requests" \
  -H "Authorization: Bearer <token>"

# Get only pending requests
curl -X GET "https://api.example.com/api/v1/leaves/requests?status=pending" \
  -H "Authorization: Bearer <token>"

# Get requests in date range
curl -X GET "https://api.example.com/api/v1/leaves/requests?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Cancel Leave Request

**Endpoint:** `POST /leaves/requests/{leave_request_id}/cancel`

**Description:** Cancel a pending leave request. Employees can only cancel their own pending requests.

**Access:** Employee only (own requests only)

**Path Parameters:**

- `leave_request_id` (integer, required): ID of the leave request to cancel

**Response:** `200 OK`

```json
{
  "id": 123,
  "company_id": 1,
  "employee_id": 5,
  "leave_type_id": 1,
  "start_date": "2024-01-15",
  "end_date": "2024-01-17",
  "number_of_days": 3,
  "reason": "Personal reasons",
  "status": "cancelled",
  "applied_date": "2024-01-10T10:30:00",
  "approved_by_user_id": null,
  "approved_date": null,
  "rejection_reason": null,
  "created_at": "2024-01-10T10:30:00",
  "updated_at": "2024-01-10T11:00:00",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": null
}
```

**Example:**

```bash
curl -X POST "https://api.example.com/api/v1/leaves/requests/123/cancel" \
  -H "Authorization: Bearer <token>"
```

**Note:** Only pending requests can be cancelled. Approved or rejected requests cannot be cancelled.

---

### 4. Get My Leave Balance

**Endpoint:** `GET /leaves/balance`

**Description:** Get leave balance for an employee. Employees see only their own balance.

**Access:** Employee (own balance), Admin (any employee's balance)

**Query Parameters:**

- `employee_id` (integer, optional): Employee ID (Admin only, defaults to current user's employee_id for employees)
- `year` (integer, optional): Year (defaults to current year)

**Response:** `200 OK`

```json
{
  "employee_id": 5,
  "employee_name": "John Doe",
  "year": 2024,
  "leave_balances": [
    {
      "id": 1,
      "company_id": 1,
      "employee_id": 5,
      "leave_type_id": 1,
      "year": 2024,
      "total_days": "15.00",
      "used_days": "5.00",
      "pending_days": "2.00",
      "available_days": "8.00",
      "carried_forward_days": "0.00",
      "leave_type_name": "Sick Leave",
      "leave_type_code": "SL",
      "employee_name": "John Doe"
    },
    {
      "id": 2,
      "company_id": 1,
      "employee_id": 5,
      "leave_type_id": 2,
      "year": 2024,
      "total_days": "12.00",
      "used_days": "3.00",
      "pending_days": "0.00",
      "available_days": "9.00",
      "carried_forward_days": "0.00",
      "leave_type_name": "Casual Leave",
      "leave_type_code": "CL",
      "employee_name": "John Doe"
    }
  ],
  "total_available_days": "17.00",
  "total_used_days": "8.00",
  "total_pending_days": "2.00"
}
```

**Example:**

```bash
# Get my leave balance for current year
curl -X GET "https://api.example.com/api/v1/leaves/balance" \
  -H "Authorization: Bearer <token>"

# Get leave balance for specific year
curl -X GET "https://api.example.com/api/v1/leaves/balance?year=2023" \
  -H "Authorization: Bearer <token>"
```

---

## Admin Endpoints

### 5. Approve/Reject Leave Request

**Endpoint:** `POST /leaves/requests/{leave_request_id}/approve`

**Description:** Approve or reject a leave request. Only admins can approve/reject leave requests.

**Access:** Admin only

**Path Parameters:**

- `leave_request_id` (integer, required): ID of the leave request to approve/reject

**Request Body:**

```json
{
  "status": "approved", // or "rejected"
  "rejection_reason": "Insufficient leave balance" // Optional, required if rejected
}
```

**Request Schema:**

- `status` (string, required): Either `"approved"` or `"rejected"`
- `rejection_reason` (string, optional): Reason for rejection (recommended if rejected)

**Response:** `200 OK`

```json
{
  "id": 123,
  "company_id": 1,
  "employee_id": 5,
  "leave_type_id": 1,
  "start_date": "2024-01-15",
  "end_date": "2024-01-17",
  "number_of_days": 3,
  "reason": "Personal reasons",
  "status": "approved",
  "applied_date": "2024-01-10T10:30:00",
  "approved_by_user_id": 2,
  "approved_date": "2024-01-11T09:00:00",
  "rejection_reason": null,
  "created_at": "2024-01-10T10:30:00",
  "updated_at": "2024-01-11T09:00:00",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": "Admin User"
}
```

**Example:**

```bash
# Approve leave request
curl -X POST "https://api.example.com/api/v1/leaves/requests/123/approve" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved"
  }'

# Reject leave request
curl -X POST "https://api.example.com/api/v1/leaves/requests/123/approve" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rejected",
    "rejection_reason": "Insufficient leave balance"
  }'
```

---

### 6. Get All Leave Requests (Admin)

**Endpoint:** `GET /leaves/requests`

**Description:** Get all leave requests in the company. Admins can filter by employee, status, and date range.

**Access:** Admin (sees all company requests), Employee (sees own requests)

**Query Parameters:**

- `employee_id` (integer, optional): Filter by employee ID
- `status` (string, optional): Filter by status (`pending`, `approved`, `rejected`, `cancelled`)
- `start_date` (date, optional): Filter by start date (format: `YYYY-MM-DD`)
- `end_date` (date, optional): Filter by end date (format: `YYYY-MM-DD`)

**Response:** `200 OK` (Same as Employee endpoint, but returns all company requests)

**Example:**

```bash
# Get all pending leave requests
curl -X GET "https://api.example.com/api/v1/leaves/requests?status=pending" \
  -H "Authorization: Bearer <admin_token>"

# Get leave requests for specific employee
curl -X GET "https://api.example.com/api/v1/leaves/requests?employee_id=5" \
  -H "Authorization: Bearer <admin_token>"

# Get leave requests in date range
curl -X GET "https://api.example.com/api/v1/leaves/requests?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer <admin_token>"
```

---

### 7. Get Employee Leave Balance (Admin)

**Endpoint:** `GET /leaves/balance`

**Description:** Get leave balance for any employee. Admins can view any employee's balance.

**Access:** Admin (any employee), Employee (own balance)

**Query Parameters:**

- `employee_id` (integer, required for admin): Employee ID
- `year` (integer, optional): Year (defaults to current year)

**Response:** `200 OK` (Same structure as Employee endpoint)

**Example:**

```bash
# Get leave balance for specific employee
curl -X GET "https://api.example.com/api/v1/leaves/balance?employee_id=5" \
  -H "Authorization: Bearer <admin_token>"

# Get leave balance for specific year
curl -X GET "https://api.example.com/api/v1/leaves/balance?employee_id=5&year=2023" \
  -H "Authorization: Bearer <admin_token>"
```

---

### 8. Create Leave Type

**Endpoint:** `POST /leaves/types`

**Description:** Create a new leave type for the company. Only admins can create leave types.

**Access:** Admin only

**Request Body:**

```json
{
  "name": "Sick Leave",
  "code": "SL",
  "description": "Leave for medical reasons",
  "max_days_per_year": 15,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": false
}
```

**Request Schema:**

- `name` (string, required, 1-100 chars): Leave type name
- `code` (string, required, 1-50 chars): Leave type code (e.g., "SL", "CL", "AL")
- `description` (string, optional): Leave type description
- `max_days_per_year` (integer, optional, >= 0): Maximum days allowed per year
- `is_paid` (boolean, default: true): Is this a paid leave
- `requires_approval` (boolean, default: true): Requires manager approval
- `can_carry_forward` (boolean, default: false): Can carry forward unused leaves

**Response:** `201 Created`

```json
{
  "id": 1,
  "company_id": 1,
  "name": "Sick Leave",
  "code": "SL",
  "description": "Leave for medical reasons",
  "max_days_per_year": 15,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": false,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00"
}
```

**Example:**

```bash
curl -X POST "https://api.example.com/api/v1/leaves/types" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sick Leave",
    "code": "SL",
    "description": "Leave for medical reasons",
    "max_days_per_year": 15,
    "is_paid": true,
    "requires_approval": true,
    "can_carry_forward": false
  }'
```

**Error:** `400 Bad Request` if leave type code already exists

```json
{
  "message": "Leave type with code 'SL' already exists",
  "error_code": "LEAVE_TYPE_CODE_EXISTS"
}
```

---

### 9. Get Leave Types

**Endpoint:** `GET /leaves/types`

**Description:** Get all leave types for the company.

**Access:** Admin, Employee

**Query Parameters:**

- `active_only` (boolean, optional, default: true): Show only active leave types

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "company_id": 1,
    "name": "Sick Leave",
    "code": "SL",
    "description": "Leave for medical reasons",
    "max_days_per_year": 15,
    "is_paid": true,
    "requires_approval": true,
    "can_carry_forward": false,
    "is_active": true,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00"
  },
  {
    "id": 2,
    "company_id": 1,
    "name": "Casual Leave",
    "code": "CL",
    "description": "Casual leave for personal reasons",
    "max_days_per_year": 12,
    "is_paid": true,
    "requires_approval": true,
    "can_carry_forward": false,
    "is_active": true,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00"
  }
]
```

**Example:**

```bash
# Get only active leave types (default)
curl -X GET "https://api.example.com/api/v1/leaves/types" \
  -H "Authorization: Bearer <token>"

# Get all leave types including inactive
curl -X GET "https://api.example.com/api/v1/leaves/types?active_only=false" \
  -H "Authorization: Bearer <token>"
```

---

### 10. Update Leave Type

**Endpoint:** `PUT /leaves/types/{leave_type_id}`

**Description:** Update a leave type. Only admins can update leave types.

**Access:** Admin only

**Path Parameters:**

- `leave_type_id` (integer, required): ID of the leave type to update

**Request Body:** (All fields optional)

```json
{
  "name": "Sick Leave Updated",
  "code": "SL",
  "description": "Updated description",
  "max_days_per_year": 20,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": true,
  "is_active": true
}
```

**Request Schema:**

- `name` (string, optional, 1-100 chars)
- `code` (string, optional, 1-50 chars)
- `description` (string, optional)
- `max_days_per_year` (integer, optional, >= 0)
- `is_paid` (boolean, optional)
- `requires_approval` (boolean, optional)
- `can_carry_forward` (boolean, optional)
- `is_active` (boolean, optional)

**Response:** `200 OK`

```json
{
  "id": 1,
  "company_id": 1,
  "name": "Sick Leave Updated",
  "code": "SL",
  "description": "Updated description",
  "max_days_per_year": 20,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": true,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-15T11:00:00"
}
```

**Example:**

```bash
curl -X PUT "https://api.example.com/api/v1/leaves/types/1" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "max_days_per_year": 20,
    "is_active": true
  }'
```

---

## Common Endpoints

### 11. Get Leave Calendar

**Endpoint:** `GET /leaves/calendar`

**Description:** Get leave calendar for a date range. Shows all approved and pending leaves in the date range (working days only, Monday-Friday).

**Access:** Admin, Employee

**Query Parameters:**

- `start_date` (date, required): Start date for calendar (format: `YYYY-MM-DD`)
- `end_date` (date, required): End date for calendar (format: `YYYY-MM-DD`)

**Response:** `200 OK`

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "leaves": [
    {
      "date": "2024-01-15",
      "employee_id": 5,
      "employee_name": "John Doe",
      "leave_type": "Sick Leave",
      "leave_type_code": "SL",
      "status": "approved",
      "number_of_days": 1
    },
    {
      "date": "2024-01-16",
      "employee_id": 5,
      "employee_name": "John Doe",
      "leave_type": "Sick Leave",
      "leave_type_code": "SL",
      "status": "approved",
      "number_of_days": 1
    },
    {
      "date": "2024-01-20",
      "employee_id": 7,
      "employee_name": "Jane Smith",
      "leave_type": "Casual Leave",
      "leave_type_code": "CL",
      "status": "pending",
      "number_of_days": 1
    }
  ]
}
```

**Example:**

```bash
curl -X GET "https://api.example.com/api/v1/leaves/calendar?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer <token>"
```

**Note:** Only working days (Monday-Friday) are included in the calendar. Weekends are excluded.

---

## Data Models

### LeaveRequestResponse

```json
{
  "id": 123,
  "company_id": 1,
  "employee_id": 5,
  "leave_type_id": 1,
  "start_date": "2024-01-15",
  "end_date": "2024-01-17",
  "number_of_days": 3,
  "reason": "Personal reasons",
  "status": "pending", // "pending", "approved", "rejected", "cancelled"
  "applied_date": "2024-01-10T10:30:00",
  "approved_by_user_id": null,
  "approved_date": null,
  "rejection_reason": null,
  "created_at": "2024-01-10T10:30:00",
  "updated_at": "2024-01-10T10:30:00",
  "employee_name": "John Doe",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "approved_by_name": null
}
```

### LeaveTypeResponse

```json
{
  "id": 1,
  "company_id": 1,
  "name": "Sick Leave",
  "code": "SL",
  "description": "Leave for medical reasons",
  "max_days_per_year": 15,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": false,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00"
}
```

### LeaveBalanceResponse

```json
{
  "id": 1,
  "company_id": 1,
  "employee_id": 5,
  "leave_type_id": 1,
  "year": 2024,
  "total_days": "15.00",
  "used_days": "5.00",
  "pending_days": "2.00",
  "available_days": "8.00",
  "carried_forward_days": "0.00",
  "leave_type_name": "Sick Leave",
  "leave_type_code": "SL",
  "employee_name": "John Doe"
}
```

### LeaveSummaryResponse

```json
{
  "employee_id": 5,
  "employee_name": "John Doe",
  "year": 2024,
  "leave_balances": [
    // Array of LeaveBalanceResponse
  ],
  "total_available_days": "17.00",
  "total_used_days": "8.00",
  "total_pending_days": "2.00"
}
```

---

## Error Codes

### Common Error Responses

**401 Unauthorized**

```json
{
  "message": "Not authenticated",
  "error_code": "UNAUTHORIZED"
}
```

**403 Forbidden**

```json
{
  "message": "Only admins can approve leave requests",
  "error_code": "PERMISSION_DENIED"
}
```

**404 Not Found**

```json
{
  "message": "Leave request not found",
  "error_code": "LEAVE_REQUEST_NOT_FOUND"
}
```

**400 Bad Request**

```json
{
  "message": "User is not associated with an employee",
  "error_code": "NO_EMPLOYEE_ASSOCIATION"
}
```

### Specific Error Codes

| Error Code                   | Description                             | HTTP Status |
| ---------------------------- | --------------------------------------- | ----------- |
| `NO_EMPLOYEE_ASSOCIATION`    | User is not associated with an employee | 400         |
| `LEAVE_TYPE_NOT_FOUND`       | Leave type not found or inactive        | 404         |
| `LEAVE_TYPE_CODE_EXISTS`     | Leave type code already exists          | 400         |
| `LEAVE_REQUEST_NOT_FOUND`    | Leave request not found                 | 404         |
| `INSUFFICIENT_LEAVE_BALANCE` | Not enough leave balance                | 400         |
| `INVALID_DATE_RANGE`         | End date must be >= start date          | 400         |
| `CANNOT_CANCEL_APPROVED`     | Cannot cancel approved/rejected request | 400         |
| `EMPLOYEE_NOT_FOUND`         | Employee not found                      | 404         |
| `EMPLOYEE_ID_REQUIRED`       | Employee ID is required                 | 400         |
| `PERMISSION_DENIED`          | User doesn't have permission            | 403         |

---

## Leave Status Values

- `pending`: Leave request is pending approval
- `approved`: Leave request has been approved
- `rejected`: Leave request has been rejected
- `cancelled`: Leave request has been cancelled by the employee

---

## Notes

1. **Date Format:** All dates should be in `YYYY-MM-DD` format
2. **Authentication:** All endpoints require Bearer token in Authorization header
3. **Company Isolation:** All operations are scoped to the authenticated user's company
4. **Leave Balance:** Automatically calculated and updated when leaves are approved/rejected
5. **Number of Days:** Automatically calculated based on start_date and end_date (excluding weekends)
6. **Leave Calendar:** Only includes working days (Monday-Friday)
7. **Role-Based Access:**
   - Employees can only see/modify their own data
   - Admins can see/modify all company data
8. **Leave Type Code:** Must be unique within a company

---

## Quick Reference

### Employee Endpoints

- `POST /leaves/apply` - Apply for leave
- `GET /leaves/requests` - Get my leave requests
- `POST /leaves/requests/{id}/cancel` - Cancel my leave request
- `GET /leaves/balance` - Get my leave balance
- `GET /leaves/types` - Get leave types
- `GET /leaves/calendar` - Get leave calendar

### Admin Endpoints

- `GET /leaves/requests` - Get all leave requests (with filters)
- `POST /leaves/requests/{id}/approve` - Approve/reject leave request
- `GET /leaves/balance?employee_id={id}` - Get any employee's leave balance
- `POST /leaves/types` - Create leave type
- `GET /leaves/types` - Get all leave types
- `PUT /leaves/types/{id}` - Update leave type
- `GET /leaves/calendar` - Get leave calendar

---

**Last Updated:** 2024-01-15
