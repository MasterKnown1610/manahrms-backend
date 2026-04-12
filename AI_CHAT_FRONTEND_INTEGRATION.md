# AI Chat — Frontend Integration Guide

Base URL: `/api/v1/ai-chat`

All endpoints require: `Authorization: Bearer <access_token>`

---

## Overview of All Endpoints

| Method | Endpoint                 | Who Can Call     | Purpose                            |
| ------ | ------------------------ | ---------------- | ---------------------------------- |
| POST   | `/ai-chat/ask`           | Admin + Employee | Send a message / perform an action |
| GET    | `/ai-chat/usage/me`      | Admin + Employee | My own usage this month            |
| GET    | `/ai-chat/usage/users`   | Admin only       | See every user's usage             |
| GET    | `/ai-chat/usage/summary` | Admin only       | Month-by-month chart data          |

---

## 1. POST `/api/v1/ai-chat/ask`

The main chat endpoint. Send any natural language message — the AI decides what to do and responds.

### Request

**Headers**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body**

```json
{
  "question": "Mark my attendance",
  "conversation_history": null
}
```

| Field                  | Type          | Required | Description                                             |
| ---------------------- | ------------- | -------- | ------------------------------------------------------- |
| `question`             | string        | Yes      | Any natural language message or command                 |
| `conversation_history` | array or null | No       | Pass previous messages to maintain context across turns |

**conversation_history format (for multi-turn chat)**

```json
{
  "question": "assign it to John",
  "conversation_history": [
    { "role": "user", "content": "create a task called Fix login bug" },
    {
      "role": "assistant",
      "content": "Done! Task created with ID 42. Should I assign it to someone?"
    }
  ]
}
```

Each item in `conversation_history`:
| Field | Type | Values |
|-------|------|--------|
| `role` | string | `"user"` or `"assistant"` |
| `content` | string | The message text |

### Response

**Success `200`**

```json
{
  "success": true,
  "message": "Done! Your attendance has been marked. Punch-in time: 09:32:45 AM. Have a great day!",
  "question": "Mark my attendance"
}
```

**Failure `200`** (errors also return HTTP 200 with `success: false`)

```json
{
  "success": false,
  "message": "You have already punched in today at 09:32 AM.",
  "question": "Mark my attendance"
}
```

| Field      | Type    | Description                                          |
| ---------- | ------- | ---------------------------------------------------- |
| `success`  | boolean | `true` = action done, `false` = something went wrong |
| `message`  | string  | The AI's response — display this in the chat UI      |
| `question` | string  | Echo of what was asked                               |

### What Admins Can Say

| Message                                                                                 | What Happens                |
| --------------------------------------------------------------------------------------- | --------------------------- |
| `"Create employee John Doe, john@acme.com, hire date 2025-04-11, password Welcome@123"` | Employee created with login |
| `"Add a high priority task Fix login bug, due April 20, assign to John"`                | Task created and assigned   |
| `"Schedule a Google Meet tomorrow 3pm to 4pm IST, link https://meet.google.com/xyz"`    | Meeting scheduled           |
| `"Show all pending leave requests"`                                                     | Lists pending leaves        |
| `"Approve leave request 5"`                                                             | Leave approved              |
| `"Reject leave 7, reason: insufficient balance"`                                        | Leave rejected              |
| `"How many employees are present today?"`                                               | Today's attendance count    |
| `"Create a department called DevOps"`                                                   | Department created          |
| `"Show dashboard summary"`                                                              | Key metrics                 |

### What Employees Can Say

| Message                                            | What Happens          |
| -------------------------------------------------- | --------------------- |
| `"Mark my attendance"` or `"Punch in"`             | Attendance punch-in   |
| `"Punch out"`                                      | Attendance punch-out  |
| `"What are my pending tasks?"`                     | Lists open tasks      |
| `"Mark task 12 as in progress"`                    | Updates task status   |
| `"Mark task 12 as done"`                           | Closes task           |
| `"Apply for sick leave from April 15 to April 17"` | Submits leave request |
| `"How many leave days do I have left?"`            | Leave balance         |
| `"Show my attendance this month"`                  | Attendance history    |
| `"Show my profile"`                                | Employee profile      |

### How to Build the Chat UI

```
Frontend stores conversation_history as an array.

On every send:
  1. Push { role: "user", content: userMessage } to history
  2. POST /ask with { question: userMessage, conversation_history: last 6 items }
  3. On response: push { role: "assistant", content: response.message } to history
  4. Display response.message in the chat bubble
  5. If success === false, show the message as an error/warning bubble
```

---

## 2. GET `/api/v1/ai-chat/usage/me`

Every user (admin or employee) can call this to see their own AI usage.

### Request

**Headers**

```
Authorization: Bearer <access_token>
```

**Query Parameters** (all optional)
| Param | Type | Default | Example |
|-------|------|---------|---------|
| `year` | integer | current year | `?year=2025` |
| `month` | integer (1–12) | current month | `?month=4` |

**Example**

```
GET /api/v1/ai-chat/usage/me?year=2025&month=4
```

### Response `200`

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
    { "date": "2025-04-05", "queries": 5, "tokens": 2600 },
    { "date": "2025-04-11", "queries": 7, "tokens": 3800 }
  ]
}
```

| Field                       | Type    | Description                                        |
| --------------------------- | ------- | -------------------------------------------------- |
| `user_id`                   | integer | Logged-in user's ID                                |
| `user_name`                 | string  | Logged-in user's name                              |
| `period`                    | string  | `"YYYY-MM"`                                        |
| `total_queries`             | integer | How many times this user called `/ask` this month  |
| `total_tokens`              | integer | Total OpenAI tokens this user consumed             |
| `company_queries_used`      | integer | Total queries used by the whole company this month |
| `company_queries_limit`     | integer | Monthly query limit from the subscription plan     |
| `company_queries_remaining` | integer | How many queries left for the company              |
| `daily_breakdown`           | array   | Per-day usage — use this for a bar/line chart      |

**`daily_breakdown` item**
| Field | Type | Description |
|-------|------|-------------|
| `date` | string | `"YYYY-MM-DD"` |
| `queries` | integer | Number of queries on this day |
| `tokens` | integer | Tokens consumed on this day |

---

## 3. GET `/api/v1/ai-chat/usage/users`

**Admin only.** See every user in the company and how much AI they consumed.

### Request

**Headers**

```
Authorization: Bearer <admin_access_token>
```

**Query Parameters** (all optional)
| Param | Type | Default | Example |
|-------|------|---------|---------|
| `year` | integer | current year | `?year=2025` |
| `month` | integer (1–12) | current month | `?month=4` |

**Example**

```
GET /api/v1/ai-chat/usage/users?year=2025&month=4
```

### Response `200`

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
    },
    {
      "user_id": 8,
      "user_name": "Priya Sharma",
      "email": "priya@acme.com",
      "role": "employee",
      "total_queries": 29,
      "total_tokens": 14260,
      "last_used": "2025-04-10T16:20:00"
    }
  ]
}
```

**Top-level fields**
| Field | Type | Description |
|-------|------|-------------|
| `period` | string | `"YYYY-MM"` |
| `company_queries_used` | integer | Total queries used by all users |
| `company_queries_limit` | integer | Monthly plan limit |
| `company_queries_remaining` | integer | Remaining this month |
| `total_tokens_this_month` | integer | Sum of all tokens used by all users |
| `users` | array | Per-user breakdown, sorted by highest token usage |

**Each user object**
| Field | Type | Description |
|-------|------|-------------|
| `user_id` | integer | User's ID |
| `user_name` | string | Full name |
| `email` | string | Email address |
| `role` | string | `"admin"` or `"employee"` |
| `total_queries` | integer | How many AI queries this user made |
| `total_tokens` | integer | Total tokens this user consumed |
| `last_used` | string or null | ISO datetime of last AI query |

**Error `403`** — if called by a non-admin

```json
{ "detail": "Admin access required" }
```

---

## 4. GET `/api/v1/ai-chat/usage/summary`

**Admin only.** Month-by-month chart data for the company.

### Request

**Headers**

```
Authorization: Bearer <admin_access_token>
```

**Query Parameters**
| Param | Type | Default | Range | Example |
|-------|------|---------|-------|---------|
| `months` | integer | 6 | 1–12 | `?months=6` |

**Example**

```
GET /api/v1/ai-chat/usage/summary?months=6
```

### Response `200`

```json
{
  "company_id": 1,
  "months_included": 6,
  "history": [
    {
      "period": "2024-11",
      "year": 2024,
      "month": 11,
      "queries_used": 210,
      "queries_limit": 1000,
      "tokens_used": 105600,
      "active_users": 4
    },
    {
      "period": "2024-12",
      "year": 2024,
      "month": 12,
      "queries_used": 380,
      "queries_limit": 1000,
      "tokens_used": 191200,
      "active_users": 7
    },
    {
      "period": "2025-01",
      "year": 2025,
      "month": 1,
      "queries_used": 512,
      "queries_limit": 1000,
      "tokens_used": 261120,
      "active_users": 11
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

**Top-level fields**
| Field | Type | Description |
|-------|------|-------------|
| `company_id` | integer | The company ID |
| `months_included` | integer | How many months are in the history array |
| `history` | array | Ordered oldest → newest |

**Each history item**
| Field | Type | Description |
|-------|------|-------------|
| `period` | string | `"YYYY-MM"` — use this as the chart x-axis label |
| `year` | integer | Year |
| `month` | integer | Month number (1–12) |
| `queries_used` | integer | Queries used that month |
| `queries_limit` | integer | Plan limit that month |
| `tokens_used` | integer | Total tokens consumed that month |
| `active_users` | integer | Number of unique users who used AI |

**Error `403`** — if called by a non-admin

```json
{ "detail": "Admin access required" }
```

---

## Error Handling

All `/ask` errors return HTTP `200` with `success: false` — check `success` not the HTTP status.

Usage endpoints return standard HTTP error codes:

| Status | When                                    |
| ------ | --------------------------------------- |
| `401`  | Missing or invalid token                |
| `403`  | Employee calling an admin-only endpoint |

---

## Frontend Usage Guide by Role

### Employee view

- Show a chat window that calls `POST /ask`
- Show a "My Usage" card using `GET /usage/me`
- Display `total_queries`, `total_tokens`, `company_queries_remaining`
- Use `daily_breakdown` for a small bar chart

### Admin view

- Same chat window with admin commands available
- Show "Team Usage" table using `GET /usage/users`
- Display each employee row: name, queries, tokens, last used
- Show a trend chart using `GET /usage/summary` — use `period` as x-axis, `tokens_used` or `queries_used` as y-axis
- Highlight users close to or exceeding company limit
