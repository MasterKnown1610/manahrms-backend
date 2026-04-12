# Task Management System — Frontend Integration Guide

Base URL for all requests: `POST/GET/PUT/DELETE https://<your-domain>/api/v1`

All endpoints require the header:
```
Authorization: Bearer <access_token>
```

---

## Table of Contents

1. [What Changed — Quick Summary](#1-what-changed--quick-summary)
2. [Role & Access Logic](#2-role--access-logic)
3. [TypeScript Types](#3-typescript-types)
4. [Task Permissions API](#4-task-permissions-api-admin-only)
5. [Core Task CRUD](#5-core-task-crud)
6. [Task Detail (Rich Single View)](#6-task-detail-rich-single-view)
7. [Comments (Issue Discussion)](#7-comments-issue-discussion)
8. [Git / Commit Tracking](#8-git--commit-tracking)
9. [UI Behaviour Guide](#9-ui-behaviour-guide)
10. [Error Reference](#10-error-reference)

---

## 1. What Changed — Quick Summary

| Area | Before | After |
|---|---|---|
| Create task | Admin only | Admin **or** employee with task-manager permission |
| View all tasks | Admin only via query | Admin + task-manager employees |
| Single task response | Basic fields only | Includes `comments[]`, `commits[]`, `created_by_user`, `branch` |
| Task create/update body | No `branch` field | Has optional `branch` field |
| Comments | Did not exist | Full CRUD on `/tasks/{id}/comments` |
| Git info | Did not exist | Full CRUD on `/tasks/{id}/commits` |
| Permission management | Did not exist | `/tasks/permissions` grant/revoke/list |

---

## 2. Role & Access Logic

There are now **three access tiers** for tasks:

| Tier | Who | What they can do |
|---|---|---|
| **Admin** | `role === "admin"` | Everything — create, assign, view all, manage permissions |
| **Task Manager** | `role === "employee"` + granted permission | Create tasks, assign to employees, view all tasks in company |
| **Regular Employee** | `role === "employee"` + no permission | View/update/comment only on tasks assigned to them |

### How to detect if the current user is a Task Manager

There is no flag in the login response. You must call the permissions list and check if the logged-in user's ID is in it.

**Recommended approach — call once after login and store in app state:**

```typescript
async function loadMyTaskPermission(myUserId: number): Promise<boolean> {
  // Only works if current user is admin; for employees,
  // a 403 means they are NOT a task manager.
  try {
    const res = await api.get('/tasks/permissions');
    const list: TaskPermissionResponse[] = res.data;
    return list.some(p => p.user_id === myUserId);
  } catch {
    return false; // 403 = not admin, not a task manager
  }
}
```

**Better approach — store a `isTaskManager` flag in user context:**

```typescript
// After login, determine access level
const user = loginResponse.user;
let isTaskManager = user.role === 'admin';

if (user.role === 'employee') {
  isTaskManager = await loadMyTaskPermission(user.id);
}

// Store in context/redux/zustand
setUserContext({ ...user, isTaskManager });
```

---

## 3. TypeScript Types

```typescript
// ─── Enums ───────────────────────────────────────────
type TaskStatus   = 'open' | 'in_progress' | 'closed';
type TaskPriority = 'low' | 'medium' | 'high';

// ─── Nested objects ───────────────────────────────────
interface UserInfo {
  id: number;
  username: string;
  full_name: string;
}

interface EmployeeInfo {
  id: number;
  employee_code: string;
  full_name: string;
}

interface ProjectInfo {
  id: number;
  name: string;
  client: string;
}

// ─── Task (list / create / update response) ───────────
interface TaskResponse {
  id: number;
  company_id: number;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;          // ISO date "YYYY-MM-DD"
  branch: string | null;            // NEW
  assigned_to_employee_id: number | null;
  created_by_user_id: number | null;
  project_id: number | null;
  project: ProjectInfo | null;
  assigned_to_employee: EmployeeInfo | null;
  created_at: string;               // ISO datetime
  updated_at: string;
}

// ─── Task Detail (single task GET) ────────────────────
interface TaskDetailResponse extends TaskResponse {
  created_by_user: UserInfo | null;  // NEW
  comments: TaskCommentResponse[];   // NEW
  commits: TaskCommitResponse[];     // NEW
}

// ─── Comment ──────────────────────────────────────────
interface TaskCommentResponse {
  id: number;
  task_id: number;
  company_id: number;
  user_id: number | null;
  content: string;
  user: UserInfo | null;
  created_at: string;
  updated_at: string;
}

// ─── Commit / Git ─────────────────────────────────────
interface TaskCommitResponse {
  id: number;
  task_id: number;
  company_id: number;
  branch: string | null;
  commit_hash: string | null;
  commit_message: string | null;
  author_name: string | null;
  commit_url: string | null;
  committed_at: string | null;      // ISO datetime
  added_by_user_id: number | null;
  added_by: UserInfo | null;
  created_at: string;
}

// ─── Permission ───────────────────────────────────────
interface TaskPermissionResponse {
  id: number;
  company_id: number;
  user_id: number;
  granted_by_user_id: number | null;
  user: UserInfo | null;
  granted_by: UserInfo | null;
  created_at: string;
}

// ─── Pagination wrapper ───────────────────────────────
interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}
```

---

## 4. Task Permissions API (Admin Only)

### 4.1 List users who have task-manager permission

```
GET /tasks/permissions
```

**Access:** Admin only (403 for anyone else)

**Response `200`:**
```json
[
  {
    "id": 1,
    "company_id": 10,
    "user_id": 42,
    "granted_by_user_id": 1,
    "user": { "id": 42, "username": "rahul_dev", "full_name": "Rahul Kumar" },
    "granted_by": { "id": 1, "username": "admin", "full_name": "Admin User" },
    "created_at": "2026-04-12T09:00:00"
  }
]
```

---

### 4.2 Grant task-manager permission

```
POST /tasks/permissions/grant
```

**Access:** Admin only

**Request body:**
```json
{ "user_id": 42 }
```

**Response `201`:** Same shape as the object above.

**Error `400`** — user already has permission:
```json
{ "detail": "User already has task-manager permission" }
```

**Error `404`** — user not found in company:
```json
{ "detail": "User not found in company" }
```

---

### 4.3 Revoke task-manager permission

```
DELETE /tasks/permissions/{user_id}
```

**Access:** Admin only

**Response `204` No Content**

**Error `404`:**
```json
{ "detail": "Task permission not found for this user" }
```

---

## 5. Core Task CRUD

### 5.1 Create Task

```
POST /tasks/create
```

**Access:** Admin OR employee with task-manager permission

**Request body:**
```json
{
  "title": "Fix login bug",
  "description": "Users cannot login with Google OAuth",
  "priority": "high",
  "due_date": "2026-04-20",
  "assigned_to_employee_id": 15,
  "project_id": 3,
  "branch": "fix/google-oauth-login"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | Yes | 3–255 characters |
| `description` | string | No | |
| `priority` | `"low"` \| `"medium"` \| `"high"` | No | Default: `"medium"` |
| `due_date` | `"YYYY-MM-DD"` | No | |
| `assigned_to_employee_id` | number | No | Must belong to same company |
| `project_id` | number | No | Must belong to same company |
| `branch` | string | No | e.g. `"feature/task-42"` |

**Response `201`:** `TaskResponse` object

**Error `403`** — not admin or task manager:
```json
{
  "success": false,
  "message": "Task-manager access required. Ask your admin to grant you permission.",
  "error_code": "TASK_MANAGER_ACCESS_REQUIRED"
}
```

---

### 5.2 Get My Tasks (Employee view)

```
GET /tasks/my-tasks?page=1&page_size=20&status=open&priority=high
```

**Access:** Any authenticated user (auto-filters to their own tasks)

**Query params:**

| Param | Type | Required | Default |
|---|---|---|---|
| `page` | number | No | 1 |
| `page_size` | number | No | 20 (max 100) |
| `status` | `"open"` \| `"in_progress"` \| `"closed"` | No | all |
| `priority` | `"low"` \| `"medium"` \| `"high"` | No | all |

**Response `200`:** `PaginatedResponse<TaskResponse>`

---

### 5.3 Query / List Tasks (with filtering & sorting)

```
POST /tasks/query
```

**Access:** Any authenticated user.
- Regular employees → only see their own assigned tasks
- Admins / task-managers → see all company tasks

**Request body:**
```json
{
  "page": 1,
  "page_size": 20,
  "sort": [{ "field": "created_at", "order": "desc" }],
  "filter": [
    { "field": "status", "operator": "eq", "value": "open" },
    { "field": "priority", "operator": "eq", "value": "high" }
  ]
}
```

**Filter operators:** `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`, `in`, `not_in`, `is_null`, `is_not_null`

**Filterable fields:** `title`, `status`, `priority`, `due_date`, `assigned_to_employee_id`, `project_id`, `branch`, `created_at`

**Response `200`:** `PaginatedResponse<TaskResponse>`

---

### 5.4 Update Task

```
PUT /tasks/{task_id}
```

**Access:**
- Admin / task-manager: can update any task field including reassignment
- Regular employee: can only update tasks assigned to them, **cannot** change `assigned_to_employee_id`

**Request body** (all fields optional, only send what you want to change):
```json
{
  "title": "Updated title",
  "description": "New description",
  "priority": "low",
  "status": "in_progress",
  "due_date": "2026-05-01",
  "assigned_to_employee_id": 20,
  "project_id": 5,
  "branch": "feature/updated-branch"
}
```

**Response `200`:** `TaskResponse`

**Error `403`** — employee trying to update someone else's task:
```json
{ "detail": "Not authorized to update this task" }
```

**Error `400`** — employee trying to reassign:
```json
{ "detail": "You do not have permission to reassign tasks" }
```

---

### 5.5 Close Task

```
POST /tasks/{task_id}/close
```

**Access:** Admin/task-manager (any task), employee (own task only)

**No request body needed.**

**Response `200`:** `TaskResponse` with `status: "closed"`

---

## 6. Task Detail (Rich Single View)

```
GET /tasks/{task_id}
```

**Access:**
- Admin / task-manager: any task
- Regular employee: only tasks assigned to them

**Response `200`:** `TaskDetailResponse`

```json
{
  "id": 7,
  "company_id": 10,
  "title": "Fix Google OAuth login",
  "description": "Users cannot login using Google OAuth on mobile.",
  "priority": "high",
  "status": "in_progress",
  "due_date": "2026-04-20",
  "branch": "fix/google-oauth-login",
  "assigned_to_employee_id": 15,
  "created_by_user_id": 1,
  "project_id": 3,
  "project": {
    "id": 3,
    "name": "Mobile App v2",
    "client": "Acme Corp"
  },
  "assigned_to_employee": {
    "id": 15,
    "employee_code": "EMP00015",
    "full_name": "Rahul Kumar"
  },
  "created_by_user": {
    "id": 1,
    "username": "admin",
    "full_name": "Admin User"
  },
  "comments": [
    {
      "id": 1,
      "task_id": 7,
      "company_id": 10,
      "user_id": 1,
      "content": "Reproduced on iOS 17. Likely a redirect URI mismatch.",
      "user": { "id": 1, "username": "admin", "full_name": "Admin User" },
      "created_at": "2026-04-12T10:30:00",
      "updated_at": "2026-04-12T10:30:00"
    }
  ],
  "commits": [
    {
      "id": 1,
      "task_id": 7,
      "company_id": 10,
      "branch": "fix/google-oauth-login",
      "commit_hash": "a3f9c12",
      "commit_message": "fix: correct redirect URI for Google OAuth",
      "author_name": "Rahul Kumar",
      "commit_url": "https://github.com/org/repo/commit/a3f9c12",
      "committed_at": "2026-04-12T14:00:00",
      "added_by_user_id": 42,
      "added_by": { "id": 42, "username": "rahul_dev", "full_name": "Rahul Kumar" },
      "created_at": "2026-04-12T14:05:00"
    }
  ],
  "created_at": "2026-04-11T08:00:00",
  "updated_at": "2026-04-12T14:05:00"
}
```

> **Note:** `comments` and `commits` are only present in this `GET /{task_id}` response. List endpoints (`/query`, `/my-tasks`) return the lighter `TaskResponse` shape without them.

---

## 7. Comments (Issue Discussion)

### 7.1 List comments

```
GET /tasks/{task_id}/comments
```

**Access:** Anyone who can access the task (sorted oldest first)

**Response `200`:** `TaskCommentResponse[]`

---

### 7.2 Add comment

```
POST /tasks/{task_id}/comments
```

**Request body:**
```json
{ "content": "I can reproduce this on Android too." }
```

**Response `201`:** `TaskCommentResponse`

```json
{
  "id": 5,
  "task_id": 7,
  "company_id": 10,
  "user_id": 42,
  "content": "I can reproduce this on Android too.",
  "user": { "id": 42, "username": "rahul_dev", "full_name": "Rahul Kumar" },
  "created_at": "2026-04-12T15:00:00",
  "updated_at": "2026-04-12T15:00:00"
}
```

---

### 7.3 Edit comment

```
PUT /tasks/{task_id}/comments/{comment_id}
```

**Access:** Author of the comment, or admin

**Request body:**
```json
{ "content": "Reproduced on Android 14 specifically." }
```

**Response `200`:** `TaskCommentResponse`

**Error `403`:**
```json
{ "detail": "You can only edit your own comments" }
```

---

### 7.4 Delete comment

```
DELETE /tasks/{task_id}/comments/{comment_id}
```

**Access:** Author of the comment, or admin

**Response `204` No Content**

**Error `403`:**
```json
{ "detail": "You can only delete your own comments" }
```

---

## 8. Git / Commit Tracking

### 8.1 List commits on a task

```
GET /tasks/{task_id}/commits
```

**Response `200`:** `TaskCommitResponse[]` (sorted oldest first)

---

### 8.2 Add a commit / branch record

```
POST /tasks/{task_id}/commits
```

**All fields are optional — send whatever you have.**

**Request body:**
```json
{
  "branch": "fix/google-oauth-login",
  "commit_hash": "a3f9c12",
  "commit_message": "fix: correct redirect URI for Google OAuth",
  "author_name": "Rahul Kumar",
  "commit_url": "https://github.com/org/repo/commit/a3f9c12",
  "committed_at": "2026-04-12T14:00:00"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `branch` | string | No | Branch name |
| `commit_hash` | string | No | Short or full SHA |
| `commit_message` | string | No | |
| `author_name` | string | No | Git author |
| `commit_url` | string | No | GitHub / GitLab link |
| `committed_at` | ISO datetime | No | When commit was made |

**Response `201`:** `TaskCommitResponse`

---

### 8.3 Remove a commit record

```
DELETE /tasks/{task_id}/commits/{commit_id}
```

**Access:** User who added the record, or admin

**Response `204` No Content**

---

## 9. UI Behaviour Guide

### Task List Page

```
If user.role === 'admin' OR user.isTaskManager:
  - Show "Create Task" button
  - Show all company tasks
  - Show "Assigned To" column
  - Show "Manage Permissions" link (admin only)
Else (regular employee):
  - Hide "Create Task" button
  - Only show tasks assigned to current user (backend enforces this automatically)
  - Hide "Assigned To" column or show it read-only
```

### Task Create / Edit Form

Add a **Branch** field:
```
Label: "Branch"
Placeholder: "e.g. feature/task-42"
Type: text input (optional)
Max length: 255
```

For **Assigned To** field:
```
If user.role === 'admin' OR user.isTaskManager:
  - Show employee dropdown (enabled)
Else:
  - Hide the field entirely (backend will reject reassignment attempts anyway)
```

### Task Detail Page

The single task view (`GET /tasks/{id}`) now returns everything in one request.
Build three sections below the task header:

#### Section 1 — Git Info
```
Show task.branch as a badge at the top (if present)

"Commits" tab:
  - List each commit: hash (shortened to 7 chars), message, author, branch, link
  - "Add Commit" button → opens a form with fields: branch, hash, message, author, URL, date
  - Delete button on each row (only show for records added by current user, or if admin)
```

#### Section 2 — Issue Discussion (Comments)
```
- Display all task.comments in a thread (oldest at top)
- Each comment shows: avatar/initials, full_name, timestamp, content
- Edit (pencil) icon — only show if comment.user_id === currentUser.id OR isAdmin
- Delete (trash) icon — same rule
- Text area at bottom with "Add Comment" button
```

#### Section 3 — Task Info Sidebar
```
New field to display: "Branch" (task.branch)
New field to display: "Created By" (task.created_by_user.full_name)
```

### Admin — Permissions Management Page

A dedicated page or modal at Settings → Task Permissions:

```
Table columns: Full Name | Username | Granted By | Date Granted | Action (Revoke)

"Grant Permission" button:
  - Search/select from employee users
  - POST /tasks/permissions/grant  { user_id: selectedUserId }

Revoke button on each row:
  - DELETE /tasks/permissions/{user_id}
  - Confirm before sending
```

---

## 10. Error Reference

| HTTP Code | `error_code` / `detail` | Meaning | What to show user |
|---|---|---|---|
| `400` | `"User already has task-manager permission"` | Duplicate grant | "This user already has task-manager access" |
| `400` | `"Employees cannot reassign tasks"` / `"You do not have permission to reassign tasks"` | Employee tried to change assignee | "You cannot reassign this task" |
| `400` | `"User is not associated with an employee"` | User account has no employee record | Prompt admin to link employee record |
| `403` | `TASK_MANAGER_ACCESS_REQUIRED` | Employee tried to create a task without permission | "You need task-manager access. Contact your admin." |
| `403` | `"Not authorized to update this task"` | Employee tried to update someone else's task | "You can only update tasks assigned to you" |
| `403` | `"Not authorized to view this task"` | Employee tried to view someone else's task | "Task not found or access denied" |
| `403` | `"You can only edit your own comments"` | Tried to edit another user's comment | "You can only edit your own comments" |
| `403` | `"You can only delete your own comments"` | Tried to delete another user's comment | "You can only delete your own comments" |
| `404` | `"Task not found"` | Task ID does not exist in company | "Task not found" |
| `404` | `"Comment not found"` | Comment ID does not exist | Toast error |
| `404` | `"Commit record not found"` | Commit ID does not exist | Toast error |
| `404` | `"Task permission not found for this user"` | Tried to revoke non-existent permission | "Permission not found" |
| `404` | `"User not found in company"` | Grant attempted for unknown user | "User not found" |

---

## Quick Reference — All Endpoints

```
# Task Permissions (Admin only)
GET    /tasks/permissions
POST   /tasks/permissions/grant
DELETE /tasks/permissions/{user_id}

# Core Tasks
POST   /tasks/create
GET    /tasks/my-tasks
POST   /tasks/query
GET    /tasks/{task_id}              ← returns full detail with comments + commits
PUT    /tasks/{task_id}
POST   /tasks/{task_id}/close

# Comments
GET    /tasks/{task_id}/comments
POST   /tasks/{task_id}/comments
PUT    /tasks/{task_id}/comments/{comment_id}
DELETE /tasks/{task_id}/comments/{comment_id}

# Git Tracking
GET    /tasks/{task_id}/commits
POST   /tasks/{task_id}/commits
DELETE /tasks/{task_id}/commits/{commit_id}
```
