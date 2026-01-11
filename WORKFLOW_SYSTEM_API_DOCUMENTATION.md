# Workflow-Driven Project Management System - API Documentation

## Overview

This document describes the complete workflow-driven project management system API. The system has three main layers:

1. **Workflow Templates** (Design Time) - Reusable workflow definitions
2. **Project Workflow Instances** (Configuration Time) - Workflow assigned to projects with user roles
3. **Task Workflow Execution** (Runtime) - Tasks following workflow from start to end

---

## Table of Contents

1. [Workflow Template APIs](#workflow-template-apis)
2. [Project Workflow APIs](#project-workflow-apis)
3. [Task Workflow APIs](#task-workflow-apis)
4. [SLA APIs](#sla-apis)
5. [Example Flows](#example-flows)

---

## Workflow Template APIs

### 1. Create Workflow Template

**POST** `/api/v1/workflows`

**Authentication**: Admin only

**Request Body**:

```json
{
  "name": "Software Development Workflow",
  "nodes": [
    {
      "node_key": "start",
      "node_type": "start",
      "role": null,
      "metadata": {
        "description": "Project initiation"
      },
      "position_x": 100,
      "position_y": 100
    },
    {
      "node_key": "development",
      "node_type": "assign",
      "role": "Developer",
      "metadata": {
        "description": "Development phase",
        "sla": {
          "response_time_hours": 24,
          "resolution_time_hours": 72
        }
      },
      "position_x": 300,
      "position_y": 100
    },
    {
      "node_key": "review",
      "node_type": "status",
      "role": "Manager",
      "metadata": {
        "description": "Code review"
      },
      "position_x": 500,
      "position_y": 100
    },
    {
      "node_key": "testing",
      "node_type": "action",
      "role": "Tester",
      "metadata": {
        "description": "QA testing"
      },
      "position_x": 500,
      "position_y": 200
    },
    {
      "node_key": "end",
      "node_type": "end",
      "role": null,
      "metadata": {
        "description": "Task complete"
      },
      "position_x": 700,
      "position_y": 100
    }
  ],
  "edges": [
    {
      "source_node_key": "start",
      "target_node_key": "development",
      "condition": null
    },
    {
      "source_node_key": "development",
      "target_node_key": "review",
      "condition": {
        "action": "complete"
      }
    },
    {
      "source_node_key": "review",
      "target_node_key": "testing",
      "condition": {
        "action": "approve"
      }
    },
    {
      "source_node_key": "review",
      "target_node_key": "development",
      "condition": {
        "action": "reject"
      }
    },
    {
      "source_node_key": "testing",
      "target_node_key": "end",
      "condition": {
        "action": "pass"
      }
    },
    {
      "source_node_key": "testing",
      "target_node_key": "development",
      "condition": {
        "action": "fail"
      }
    }
  ]
}
```

**Response** (201 Created):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "company_id": 1,
  "name": "Software Development Workflow",
  "version": 1,
  "is_active": true,
  "created_at": "2024-01-20T10:00:00",
  "updated_at": "2024-01-20T10:00:00",
  "nodes": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "node_key": "start",
      "node_type": "start",
      "role": null,
      "metadata": {
        "description": "Project initiation"
      },
      "position_x": 100,
      "position_y": 100,
      "created_at": "2024-01-20T10:00:00"
    }
    // ... more nodes
  ],
  "edges": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "source_node_id": "660e8400-e29b-41d4-a716-446655440001",
      "target_node_id": "660e8400-e29b-41d4-a716-446655440003",
      "source_node_key": "start",
      "target_node_key": "development",
      "condition": null,
      "created_at": "2024-01-20T10:00:00"
    }
    // ... more edges
  ]
}
```

### 2. List Workflows

**GET** `/api/v1/workflows?include_inactive=false`

**Response** (200 OK):

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Software Development Workflow",
    "version": 1,
    "is_active": true,
    "created_at": "2024-01-20T10:00:00"
  }
]
```

### 3. Get Workflow

**GET** `/api/v1/workflows/{workflow_id}`

**Response** (200 OK): Same format as Create response

### 4. Update Workflow

**PUT** `/api/v1/workflows/{workflow_id}`

**Request Body** (all fields optional):

```json
{
  "name": "Updated Workflow Name",
  "nodes": [...],
  "edges": [...]
}
```

**Note**: Updating nodes/edges increments version automatically.

### 5. Delete Workflow

**DELETE** `/api/v1/workflows/{workflow_id}`

**Response** (200 OK):

```json
{
  "message": "Workflow deleted successfully"
}
```

---

## Project Workflow APIs

### 1. Assign Workflow to Project

**POST** `/api/v1/projects/{project_id}/assign-workflow`

**Authentication**: Admin only

**Request Body**:

```json
{
  "workflow_template_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (201 Created):

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440004",
  "project_id": 123,
  "workflow_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_template": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Software Development Workflow",
    "version": 1,
    "is_active": true,
    "created_at": "2024-01-20T10:00:00"
  },
  "users": [],
  "created_at": "2024-01-20T11:00:00"
}
```

### 2. Configure Users for Project Workflow

**POST** `/api/v1/projects/{project_id}/configure-users`

**Authentication**: Admin only

**Request Body**:

```json
{
  "user_assignments": [
    {
      "role": "Developer",
      "user_id": 10
    },
    {
      "role": "Tester",
      "user_id": 11
    },
    {
      "role": "Manager",
      "user_id": 12
    }
  ]
}
```

**Response** (201 Created):

```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440005",
    "role": "Developer",
    "user_id": 10,
    "user": {
      "id": 10,
      "username": "john_dev",
      "full_name": "John Developer",
      "email": "john@example.com"
    },
    "created_at": "2024-01-20T11:30:00"
  }
  // ... more assignments
]
```

### 3. Get Project Workflow

**GET** `/api/v1/projects/{project_id}/workflow`

**Response** (200 OK): Same format as Assign Workflow response

---

## Task Workflow APIs

### 1. Create Task with Workflow

**POST** `/api/v1/projects/{project_id}/tasks`

**Request Body**:

```json
{
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication system",
  "priority": "high",
  "due_date": "2024-02-15T00:00:00"
}
```

**Response** (201 Created):

```json
{
  "id": 456,
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication system",
  "status": "open",
  "priority": "high",
  "project_id": 123,
  "current_node_id": "660e8400-e29b-41d4-a716-446655440001",
  "current_node_key": "start",
  "current_node_type": "start",
  "current_role": null,
  "project_workflow_id": "880e8400-e29b-41d4-a716-446655440004",
  "state_history": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440006",
      "task_id": 456,
      "from_node_id": null,
      "to_node_id": "660e8400-e29b-41d4-a716-446655440001",
      "from_node_key": null,
      "to_node_key": "start",
      "action": "created",
      "performed_by": 1,
      "performer_name": "Admin User",
      "created_at": "2024-01-20T12:00:00"
    }
  ],
  "created_at": "2024-01-20T12:00:00",
  "updated_at": "2024-01-20T12:00:00"
}
```

**What Happens**:

- Task is created
- Workflow is initialized at start node
- SLA tracking begins for start node
- Initial state history record is created

### 2. Get Task with Workflow

**GET** `/api/v1/projects/tasks/{task_id}`

**Response** (200 OK): Same format as Create Task response, with full state history

### 3. Transition Task

**POST** `/api/v1/projects/tasks/{task_id}/transition`

**Request Body**:

```json
{
  "action": "complete",
  "condition_data": {
    "status": "done"
  }
}
```

**Response** (200 OK):

```json
{
  "id": 456,
  "title": "Implement user authentication",
  "status": "in_progress",
  "current_node_id": "660e8400-e29b-41d4-a716-446655440003",
  "current_node_key": "development",
  "current_node_type": "assign",
  "current_role": "Developer",
  "state_history": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440006",
      "from_node_key": null,
      "to_node_key": "start",
      "action": "created",
      "created_at": "2024-01-20T12:00:00"
    },
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440007",
      "from_node_key": "start",
      "to_node_key": "development",
      "action": "complete",
      "performed_by": 1,
      "created_at": "2024-01-20T13:00:00"
    }
  ]
}
```

**What Happens**:

- Validates edge condition matches action
- Updates task current_node_id
- Creates state history record
- Updates SLA for old node (marks as met/breached)
- Initializes SLA for new node
- Assigns task to user based on node role (if assign node)

---

## SLA APIs

### 1. Get Task SLA

**GET** `/api/v1/tasks/{task_id}/sla`

**Response** (200 OK):

```json
{
  "task_id": 456,
  "current_sla": {
    "id": "cc0e8400-e29b-41d4-a716-446655440008",
    "task_id": 456,
    "workflow_node_id": "660e8400-e29b-41d4-a716-446655440003",
    "workflow_node_key": "development",
    "sla_status": "in_progress",
    "started_at": "2024-01-20T13:00:00",
    "response_deadline": "2024-01-21T13:00:00",
    "resolution_deadline": "2024-01-23T13:00:00",
    "breached_at": null,
    "created_at": "2024-01-20T13:00:00"
  },
  "all_sla_tracking": [
    {
      "id": "cc0e8400-e29b-41d4-a716-446655440008",
      "workflow_node_key": "development",
      "sla_status": "in_progress",
      "started_at": "2024-01-20T13:00:00",
      "response_deadline": "2024-01-21T13:00:00",
      "resolution_deadline": "2024-01-23T13:00:00"
    }
  ],
  "breached_count": 0,
  "met_count": 0,
  "pending_count": 1
}
```

### 2. Check SLA Breach

**POST** `/api/v1/tasks/{task_id}/sla/check`

**Response** (200 OK):

```json
{
  "task_id": 456,
  "breached_count": 0,
  "updated_count": 0,
  "checked_at": "2024-01-20T14:00:00"
}
```

---

## Example Flows

### Complete Workflow Lifecycle

#### Step 1: Create Workflow Template

```bash
POST /api/v1/workflows
# Creates workflow with nodes and edges
# Returns workflow_id: "550e8400-e29b-41d4-a716-446655440000"
```

#### Step 2: Assign Workflow to Project

```bash
POST /api/v1/projects/123/assign-workflow
{
  "workflow_template_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Step 3: Configure Users

```bash
POST /api/v1/projects/123/configure-users
{
  "user_assignments": [
    {"role": "Developer", "user_id": 10},
    {"role": "Tester", "user_id": 11},
    {"role": "Manager", "user_id": 12}
  ]
}
```

#### Step 4: Create Task

```bash
POST /api/v1/projects/123/tasks
{
  "title": "Fix login bug",
  "description": "Users cannot login",
  "priority": "high"
}
# Task starts at "start" node
# SLA tracking begins
```

#### Step 5: Transition Task

```bash
POST /api/v1/projects/tasks/456/transition
{
  "action": "complete"
}
# Moves from "start" to "development"
# Assigns to Developer (user_id: 10)
# SLA tracking starts for development node
```

#### Step 6: Check SLA

```bash
GET /api/v1/tasks/456/sla
# Returns current SLA status and deadlines
```

#### Step 7: Continue Transitions

```bash
# Developer completes work
POST /api/v1/projects/tasks/456/transition
{"action": "complete"}
# Moves to "review" node
# Assigns to Manager (user_id: 12)

# Manager approves
POST /api/v1/projects/tasks/456/transition
{"action": "approve"}
# Moves to "testing" node
# Assigns to Tester (user_id: 11)

# Tester passes
POST /api/v1/projects/tasks/456/transition
{"action": "pass"}
# Moves to "end" node
# Task status becomes "closed"
```

---

## Node Types

- **start**: Entry point of workflow (required)
- **assign**: Assigns task to user based on role
- **status**: Status check/review point
- **action**: Action required from user
- **end**: Exit point of workflow

---

## Edge Conditions

Edges can have conditions that must be met for transition:

```json
{
  "condition": {
    "action": "approve" // Action must match
  }
}
```

Or:

```json
{
  "condition": {
    "action": "complete",
    "status": "done" // Multiple conditions
  }
}
```

If condition is `null`, edge is always available.

---

## SLA Definitions

SLA can be defined per node in metadata:

```json
{
  "node_key": "development",
  "node_type": "assign",
  "metadata": {
    "sla": {
      "response_time_hours": 24,
      "resolution_time_hours": 72,
      "escalation_role": "Manager"
    }
  }
}
```

SLA tracking automatically:

- Starts when task enters node
- Calculates deadlines
- Marks as breached if exceeded
- Can escalate to configured role

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

Common status codes:

- `400`: Bad Request (validation errors)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

---

## Notes

1. **Versioning**: Workflow templates are versioned. When updated, version increments automatically.

2. **Multi-tenancy**: All operations are company-scoped. Users can only access workflows from their company.

3. **Soft Delete**: Workflows are soft-deleted (is_active = false), not permanently removed.

4. **SLA Tracking**: SLA tracking is automatic when tasks enter nodes with SLA definitions.

5. **Task Assignment**: Tasks are automatically assigned to users when entering "assign" type nodes based on configured role-user mappings.

6. **State History**: All workflow transitions are tracked in task_state_history for audit trail.

---

This system provides a complete workflow-driven project management solution with SLA tracking, user role management, and full audit trails.
