# AI Chat — Agentic API Documentation

Base URL: `/api/v1/ai-chat`

All endpoints require `Authorization: Bearer <token>`.

---

## How It Works

1. User sends a natural language message to `/ask`
2. The agent uses OpenAI Function Calling to decide which HRMS action to take
3. It executes the action directly on the database (create employee, punch in, etc.)
4. Returns a human-friendly confirmation
5. Real token counts from OpenAI are recorded per-user in the `ai_usage` table

---

## POST `/api/v1/ai-chat/ask`

The single endpoint for everything — queries, actions, and commands.

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "question": "Mark my attendance",
  "conversation_history": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Natural language message or command |
| `conversation_history` | array | No | Previous messages for multi-turn context |

**Conversation history format (multi-turn)**
```json
{
  "question": "Assign it to John",
  "conversation_history": [
    { "role": "user", "content": "Create a task called Fix login bug" },
    { "role": "assistant", "content": "Done! Task created with ID 42." }
  ]
}
```

**Response `200`**
```json
{
  "success": true,
  "message": "Done! Your attendance has been marked. Punch-in time: 09:32:45 AM. Have a great day!",
  "question": "Mark my attendance"
}
```

**Error Response**
```json
{
  "success": false,
  "message": "You have already punched in today at 09:32 AM.",
  "question": "Mark my attendance"
}
```

---

### What Admins Can Ask

| Example Message | Action Performed |
|----------------|-----------------|
| `"Create employee John Doe, john@acme.com, hire date 2025-04-11, password Welcome@123"` | Creates employee + user account |
| `"Add a high priority task Fix API bug and assign to John"` | Creates and assigns task |
| `"Schedule a Zoom meeting tomorrow 3pm to 4pm IST"` | Creates meeting |
| `"Show all pending leave requests"` | Lists pending leaves |
| `"Approve leave request 5"` | Approves leave |
| `"Reject leave 7, reason: insufficient balance"` | Rejects leave with reason |
| `"How many employees are present today?"` | Attendance report for today |
| `"List all open tasks assigned to Priya"` | Filtered task list |
| `"Create a department called DevOps"` | Creates department |
| `"Show me the dashboard summary"` | Employees, tasks, attendance count |
| `"List all projects"` | Active projects |

### What Employees Can Ask

| Example Message | Action Performed |
|----------------|-----------------|
| `"Mark my attendance"` / `"Punch in"` | Punch-in for today |
| `"Punch out"` | Punch-out for today |
| `"What are my pending tasks?"` | Tasks with status=open |
| `"Mark task 12 as in progress"` | Updates task status |
| `"Mark task 12 as done"` | Updates task status to closed |
| `"Apply for sick leave from April 15 to April 17"` | Submits leave request |
| `"How many leave days do I have left?"` | Leave balance for all types |
| `"Show my attendance this month"` | Attendance records |
| `"What leave types are available?"` | Lists leave types with IDs |
| `"Show my profile"` | Employee profile info |

---

## GET `/api/v1/ai-chat/usage/me`

Get the current user's own AI usage for a given month.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `year` | int | current year | Year to query |
| `month` | int | current month | Month (1–12) |

**Response `200`**
```json
{
  "user_id": 5,
  "user_name": "John Doe",
  "period": "2025-04",
  "total_queries": 28,
  "total_tokens": 14320,
  "company_queries_used": 142,
  "company_queries_limit": 1000,
  "company_queries_remaining": 858,
  "daily_breakdown": [
    { "date": "2025-04-01", "queries": 3, "tokens": 1540 },
    { "date": "2025-04-02", "queries": 5, "tokens": 2200 },
    { "date": "2025-04-11", "queries": 7, "tokens": 3800 }
  ]
}
```

---

## GET `/api/v1/ai-chat/usage/users`

**Admin only.** Per-user breakdown of AI usage for the company this month.

**Headers:** `Authorization: Bearer <token>` (must be admin)

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `year` | int | current year | Year to query |
| `month` | int | current month | Month (1–12) |

**Response `200`**
```json
{
  "period": "2025-04",
  "company_queries_used": 142,
  "company_queries_limit": 1000,
  "company_queries_remaining": 858,
  "total_tokens_this_month": 71800,
  "users": [
    {
      "user_id": 3,
      "user_name": "Admin User",
      "email": "admin@acme.com",
      "role": "admin",
      "total_queries": 85,
      "total_tokens": 43200,
      "last_used": "2025-04-11T14:32:00"
    },
    {
      "user_id": 5,
      "user_name": "John Doe",
      "email": "john@acme.com",
      "role": "employee",
      "total_queries": 28,
      "total_tokens": 14320,
      "last_used": "2025-04-11T09:45:00"
    }
  ]
}
```

**Error:** `403` — Admin access required

---

## GET `/api/v1/ai-chat/usage/summary`

**Admin only.** Month-by-month usage history for charting on the frontend.

**Headers:** `Authorization: Bearer <token>` (must be admin)

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `months` | int | 6 | Number of past months to include (1–12) |

**Response `200`**
```json
{
  "company_id": 1,
  "months_included": 6,
  "history": [
    {
      "period": "2024-11",
      "year": 2024,
      "month": 11,
      "queries_used": 320,
      "queries_limit": 1000,
      "tokens_used": 158400,
      "active_users": 12
    },
    {
      "period": "2024-12",
      "year": 2024,
      "month": 12,
      "queries_used": 410,
      "queries_limit": 1000,
      "tokens_used": 204800,
      "active_users": 15
    },
    {
      "period": "2025-01",
      "year": 2025,
      "month": 1,
      "queries_used": 512,
      "queries_limit": 1000,
      "tokens_used": 261120,
      "active_users": 18
    },
    {
      "period": "2025-04",
      "year": 2025,
      "month": 4,
      "queries_used": 142,
      "queries_limit": 1000,
      "tokens_used": 71800,
      "active_users": 9
    }
  ]
}
```

**Error:** `403` — Admin access required

---

## Token Tracking Details

| What | How |
|------|-----|
| **Source** | Real `response.usage.total_tokens` from OpenAI API — not estimated |
| **Multi-round** | Tokens from all tool-call rounds in a single message are summed |
| **Storage** | Each query → one row in `ai_usage` table (`user_id`, `tokens_used`, `created_at`) |
| **Monthly counter** | `company_ai_usage` table tracks `queries_used` per company per month |
| **Limit enforcement** | `check_ai_usage_limit()` blocks the query if `queries_used >= total_limit` |

---

## Quick Reference

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/ai-chat/ask` | All users | Send a message / perform an action |
| GET | `/ai-chat/usage/me` | All users | My usage this month |
| GET | `/ai-chat/usage/users` | Admin only | Per-user breakdown |
| GET | `/ai-chat/usage/summary` | Admin only | Month-by-month chart data |
