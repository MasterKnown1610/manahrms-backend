# Leave Management System - Implementation Summary

## ✅ What Was Implemented

A complete leave management system for employees with the following features:

### 1. **Database Models**

- `LeaveType` - Types of leaves (Sick, Casual, Annual, etc.)
- `LeaveRequest` - Employee leave applications
- `LeaveBalance` - Employee leave balances per leave type per year

### 2. **Core Features**

- ✅ Apply for leave
- ✅ View leave requests
- ✅ Approve/Reject leave requests (Admin only)
- ✅ Cancel leave requests (Employee only)
- ✅ View leave balance
- ✅ Leave calendar view
- ✅ Leave type management (Admin only)

### 3. **Business Logic**

- ✅ Working days calculation (excludes weekends)
- ✅ Automatic balance tracking
- ✅ Balance validation before applying
- ✅ Pending/Used/Available days tracking
- ✅ Year-based balance management

---

## 📋 API Endpoints

### Leave Requests

#### 1. Apply for Leave

```
POST /api/v1/leaves/apply
```

**Request Body:**

```json
{
  "leave_type_id": 1,
  "start_date": "2024-12-01",
  "end_date": "2024-12-05",
  "reason": "Family emergency"
}
```

#### 2. Get Leave Requests

```
GET /api/v1/leaves/requests?employee_id=1&status=pending&start_date=2024-12-01&end_date=2024-12-31
```

**Query Parameters:**

- `employee_id` (optional) - Filter by employee
- `status` (optional) - Filter by status (pending, approved, rejected, cancelled)
- `start_date` (optional) - Filter by start date
- `end_date` (optional) - Filter by end date

#### 3. Approve/Reject Leave Request

```
POST /api/v1/leaves/requests/{leave_request_id}/approve
```

**Request Body:**

```json
{
  "status": "approved", // or "rejected"
  "rejection_reason": "Insufficient coverage" // optional, required if rejected
}
```

**Note:** Admin only

#### 4. Cancel Leave Request

```
POST /api/v1/leaves/requests/{leave_request_id}/cancel
```

**Note:** Employee can only cancel their own pending requests

### Leave Balance

#### 5. Get Leave Balance

```
GET /api/v1/leaves/balance?employee_id=1&year=2024
```

**Query Parameters:**

- `employee_id` (optional) - Employee ID (admin can view any, employee sees own)
- `year` (optional) - Year (defaults to current year)

**Response:**

```json
{
  "employee_id": 1,
  "employee_name": "John Doe",
  "year": 2024,
  "leave_balances": [
    {
      "leave_type_name": "Sick Leave",
      "leave_type_code": "SL",
      "total_days": 10,
      "used_days": 3,
      "pending_days": 2,
      "available_days": 5,
      "carried_forward_days": 0
    }
  ],
  "total_available_days": 5,
  "total_used_days": 3,
  "total_pending_days": 2
}
```

### Leave Calendar

#### 6. Get Leave Calendar

```
GET /api/v1/leaves/calendar?start_date=2024-12-01&end_date=2024-12-31
```

**Query Parameters:**

- `start_date` (required) - Calendar start date
- `end_date` (required) - Calendar end date

**Response:**
Shows all approved and pending leaves in the date range

### Leave Type Management (Admin Only)

#### 7. Create Leave Type

```
POST /api/v1/leaves/types
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

#### 8. Get Leave Types

```
GET /api/v1/leaves/types?active_only=true
```

#### 9. Update Leave Type

```
PUT /api/v1/leaves/types/{leave_type_id}
```

---

## 🔐 Permissions

### Employees Can:

- ✅ Apply for leave
- ✅ View their own leave requests
- ✅ View their own leave balance
- ✅ Cancel their own pending leave requests
- ✅ View leave calendar

### Admins Can:

- ✅ Everything employees can do
- ✅ View all leave requests in company
- ✅ Approve/Reject leave requests
- ✅ View any employee's leave balance
- ✅ Create/Update leave types

---

## 📊 Database Schema

### LeaveType Table

- `id` - Primary key
- `company_id` - Foreign key to companies
- `name` - Leave type name (e.g., "Sick Leave")
- `code` - Leave type code (e.g., "SL")
- `max_days_per_year` - Maximum days allowed
- `is_paid` - Is paid leave
- `requires_approval` - Requires approval
- `can_carry_forward` - Can carry forward

### LeaveRequest Table

- `id` - Primary key
- `company_id` - Foreign key to companies
- `employee_id` - Foreign key to employees
- `leave_type_id` - Foreign key to leave_types
- `start_date` - Leave start date
- `end_date` - Leave end date
- `number_of_days` - Calculated working days
- `reason` - Reason for leave
- `status` - pending/approved/rejected/cancelled
- `approved_by_user_id` - Approver user ID
- `approved_date` - Approval date
- `rejection_reason` - Rejection reason

### LeaveBalance Table

- `id` - Primary key
- `company_id` - Foreign key to companies
- `employee_id` - Foreign key to employees
- `leave_type_id` - Foreign key to leave_types
- `year` - Year for this balance
- `total_days` - Total allocated days
- `used_days` - Days used (approved)
- `pending_days` - Days pending approval
- `available_days` - Available days (calculated)
- `carried_forward_days` - Days from previous year

---

## 🚀 Setup Instructions

### 1. Database Tables

The tables will be created automatically when you start the server (via `init_db.py`).

### 2. Create Leave Types

First, create leave types for your company:

```bash
POST /api/v1/leaves/types
{
  "name": "Sick Leave",
  "code": "SL",
  "max_days_per_year": 10,
  "is_paid": true,
  "requires_approval": true
}

POST /api/v1/leaves/types
{
  "name": "Casual Leave",
  "code": "CL",
  "max_days_per_year": 12,
  "is_paid": true,
  "requires_approval": true
}

POST /api/v1/leaves/types
{
  "name": "Annual Leave",
  "code": "AL",
  "max_days_per_year": 20,
  "is_paid": true,
  "requires_approval": true,
  "can_carry_forward": true
}
```

### 3. Initialize Leave Balances

Leave balances are automatically created when:

- An employee applies for leave
- You query an employee's leave balance

The system automatically:

- Creates balance records for all active leave types
- Sets `total_days` based on `max_days_per_year` from leave type
- Initializes all counters to 0

---

## 💡 Usage Examples

### Example 1: Employee Applies for Leave

```bash
POST /api/v1/leaves/apply
Authorization: Bearer <employee_token>
{
  "leave_type_id": 1,
  "start_date": "2024-12-15",
  "end_date": "2024-12-17",
  "reason": "Medical appointment"
}
```

**Response:**

- Leave request created with status "pending"
- Leave balance updated: `pending_days` increased
- `available_days` decreased

### Example 2: Admin Approves Leave

```bash
POST /api/v1/leaves/requests/1/approve
Authorization: Bearer <admin_token>
{
  "status": "approved"
}
```

**Response:**

- Leave request status changed to "approved"
- Leave balance updated: `pending_days` decreased, `used_days` increased

### Example 3: View Leave Balance

```bash
GET /api/v1/leaves/balance?employee_id=1&year=2024
Authorization: Bearer <token>
```

**Response:**
Shows all leave types with balances for the employee

---

## 🔄 Workflow

1. **Admin creates leave types** → Defines available leave types
2. **Employee applies for leave** → Creates pending request, updates balance
3. **Admin reviews request** → Approves or rejects
4. **If approved** → Balance updated (pending → used)
5. **If rejected** → Balance updated (pending removed)

---

## 📝 Notes

- **Working Days Calculation**: Only counts Monday-Friday (excludes weekends)
- **Balance Validation**: System checks available balance before allowing leave application
- **Automatic Balance Creation**: Balances are created automatically when needed
- **Year-based**: Each year has separate balances
- **Carry Forward**: Support for carry forward (manual implementation needed for year-end)

---

## 🎯 Next Steps (Optional Enhancements)

1. **Holiday Calendar Integration** - Exclude holidays from working days
2. **Half-day Leaves** - Support for half-day leave requests
3. **Leave Encashment** - Cash out unused leaves
4. **Auto-approval** - Auto-approve certain leave types
5. **Notifications** - Email notifications for leave status changes
6. **Leave Reports** - Generate leave reports
7. **Year-end Processing** - Automatic carry forward processing

---

## ✅ Testing Checklist

- [ ] Create leave types (admin)
- [ ] Apply for leave (employee)
- [ ] View leave requests
- [ ] Approve leave request (admin)
- [ ] Reject leave request (admin)
- [ ] Cancel leave request (employee)
- [ ] View leave balance
- [ ] View leave calendar
- [ ] Test insufficient balance scenario
- [ ] Test past date validation
- [ ] Test invalid date range

---

## 🐛 Common Issues

### Issue: "Insufficient leave balance"

**Solution:** Check leave balance and ensure employee has enough days

### Issue: "Cannot apply for leave in the past"

**Solution:** Start date must be today or in the future

### Issue: "Leave type not found"

**Solution:** Ensure leave type exists and is active for the company

---

## 📚 Files Created/Modified

### New Files:

- `app/api/v1/models/leave_model.py` - Database models
- `app/api/v1/schemas/leave_schema.py` - Pydantic schemas
- `app/api/v1/services/leave_service.py` - Business logic
- `app/api/v1/routes/leaves.py` - API routes

### Modified Files:

- `app/api/v1/models/company_model.py` - Added leave_types relationship
- `app/api/v1/models/employee_model.py` - Added leave relationships
- `app/db/base.py` - Added leave model imports
- `app/api/router.py` - Added leaves router
- `app/db/init_db.py` - Added leave tables to required tables

---

**Leave Management System is now fully implemented and ready to use! 🎉**
