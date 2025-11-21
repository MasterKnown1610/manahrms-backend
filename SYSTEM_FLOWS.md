# HRMS SaaS Backend - System Flows Documentation

## Table of Contents
1. [Department Access Management Flow](#department-access-management-flow)
2. [Project Management Flow](#project-management-flow)
3. [Task Management Integration](#task-management-integration)
4. [User Workflows](#user-workflows)
5. [Admin Workflows](#admin-workflows)

---

## Department Access Management Flow

### Overview
The department access management system allows administrators to control which employees can view and access specific departments. This ensures data privacy and proper access control within the organization.

### Access Control Rules

**Admin Users:**
- Admins automatically have access to ALL departments within their company
- Admins can view all departments without any restrictions
- Admins can grant or revoke access to any employee for any department
- Admins can see which users have access to which departments

**Employee Users:**
- Employees can ONLY view departments they have been explicitly granted access to
- If an employee tries to access a department without permission, they receive a "Forbidden" error
- Employees cannot see departments they don't have access to in the department list
- Employees cannot grant or revoke access (only admins can do this)

### Granting Department Access Flow

1. **Admin Initiates Access Grant**
   - Admin logs into the system
   - Admin navigates to the department access management section
   - Admin selects a specific department
   - Admin selects a specific employee/user to grant access to

2. **System Validates Request**
   - System checks if the admin belongs to the same company as the department
   - System checks if the employee belongs to the same company as the department
   - System checks if the department exists and is active
   - System checks if the user exists and is active

3. **Access Record Creation**
   - If access doesn't exist, system creates a new access record
   - If access exists but was previously revoked, system reactivates it
   - System records who granted the access (the admin user)
   - System sets the access as active

4. **Employee Can Now Access**
   - Employee can now view the department details
   - Employee can see the department in their department list
   - Employee can access all information related to that department

### Revoking Department Access Flow

1. **Admin Initiates Access Revocation**
   - Admin logs into the system
   - Admin navigates to the department access management section
   - Admin selects a specific department
   - Admin selects a specific employee/user to revoke access from

2. **System Validates Request**
   - System checks if the admin belongs to the same company
   - System checks if an active access record exists for this user-department combination
   - System verifies the access is currently active

3. **Access Deactivation**
   - System marks the access record as inactive (soft delete)
   - The access is revoked but the record is kept for audit purposes
   - System does not delete the record, just deactivates it

4. **Employee Loses Access**
   - Employee can no longer view the department details
   - Department disappears from employee's department list
   - If employee tries to access, they receive a "Forbidden" error

### Viewing Department Access Information Flow

1. **Admin Views Department Users**
   - Admin selects a department
   - Admin requests to see all users with access to that department
   - System returns a list of all users who have active access
   - List includes user details and when access was granted

2. **Admin Views User Departments**
   - Admin selects a specific user
   - Admin requests to see all departments that user can access
   - System returns a list of all departments the user has access to
   - List includes department details and access information

### Employee Department Viewing Flow

1. **Employee Requests Department List**
   - Employee logs into the system
   - Employee requests to see all available departments
   - System checks the employee's access records
   - System returns ONLY departments the employee has been granted access to

2. **Employee Requests Specific Department**
   - Employee requests details of a specific department by ID
   - System checks if employee has access to that department
   - If access exists and is active, system returns department details
   - If no access, system returns "Forbidden" error

3. **Access Check Process**
   - System queries the department_access table
   - System looks for active records matching user_id and department_id
   - System verifies the department belongs to the same company
   - System verifies the department is active

---

## Project Management Flow

### Overview
The project management system allows administrators to create and manage projects with clients, timelines, and project leads. Projects are integrated with the task management system, allowing tasks to be organized under specific projects.

### Project Creation Flow

1. **Admin Initiates Project Creation**
   - Admin logs into the system
   - Admin navigates to project management section
   - Admin clicks "Create New Project"

2. **Admin Provides Project Information**
   - Admin enters project name (required, must be unique within company)
   - Admin enters client name (required)
   - Admin enters number of days (required, must be greater than 0)
   - Admin enters target date/deadline (required)
   - Admin optionally selects a project lead from available users

3. **System Validates Information**
   - System checks if project name already exists in the company
   - System validates number of days is positive
   - System validates target date is in the future (or allows past dates)
   - If project lead is selected, system verifies the user exists and is active in the company

4. **Project Record Creation**
   - System creates new project record in the projects table
   - System links project to the company
   - System sets project as active by default
   - System records creation timestamp

5. **Project Available for Use**
   - Project appears in project list
   - Project can now be used when creating tasks
   - Project lead (if assigned) can view the project in their project list

### Project Lead Assignment Flow

1. **Selecting Project Lead**
   - During project creation or update, admin selects a user as project lead
   - Project lead must be an active user in the same company
   - Project lead can be an admin or an employee

2. **Project Lead Capabilities**
   - Project lead can view their assigned projects via "my-projects" endpoint
   - Project lead can see all tasks associated with their projects
   - Project lead has visibility into project progress and task statistics

3. **Changing Project Lead**
   - Admin can update project to assign a different project lead
   - System validates the new lead belongs to the company
   - Previous lead loses special project visibility (unless they have other access)

### Project Update Flow

1. **Admin Initiates Update**
   - Admin selects an existing project
   - Admin clicks "Edit Project"
   - Admin modifies any of the project fields (name, client, days, target date, lead)

2. **System Validates Changes**
   - If name is changed, system checks for uniqueness
   - If project lead is changed, system validates the new lead exists
   - System ensures all updated values meet validation requirements

3. **Update Applied**
   - System updates only the fields that were changed
   - System records update timestamp
   - Changes are immediately reflected in the project

### Project Deactivation Flow

1. **Admin Initiates Deactivation**
   - Admin selects a project
   - Admin clicks "Deactivate Project"
   - System confirms the action

2. **Soft Delete Process**
   - System marks project as inactive (is_active = false)
   - Project is not deleted from database
   - Project remains linked to existing tasks
   - Project no longer appears in active project lists

3. **Impact on Tasks**
   - Tasks associated with the project remain in the system
   - Tasks can still be viewed and managed
   - New tasks cannot be assigned to deactivated projects

### Viewing Projects Flow

1. **Admin Views All Projects**
   - Admin requests project list
   - System returns all projects for the company
   - Projects can be filtered by active status
   - Projects can be filtered by project lead
   - Results are paginated

2. **Project Lead Views Their Projects**
   - Project lead requests "my-projects"
   - System queries projects where project_lead_id matches user
   - System returns only active projects where user is the lead
   - Results show project details and basic information

3. **Viewing Project Details**
   - User requests specific project by ID
   - System verifies project belongs to user's company
   - System returns project details including:
     - Project information (name, client, days, target date)
     - Project lead information
     - Task statistics (total tasks, open tasks, completed tasks)
   - System calculates task statistics from associated tasks

---

## Task Management Integration

### Overview
Tasks are now integrated with projects, allowing tasks to be organized and tracked within specific projects. This provides better project management and task organization capabilities.

### Creating Tasks for Projects Flow

1. **Admin Creates Task**
   - Admin navigates to task creation
   - Admin enters task details (title, description, priority, due date)
   - Admin optionally selects a project from available projects
   - Admin optionally assigns task to an employee

2. **System Validates Project Assignment**
   - If project is selected, system verifies project exists
   - System verifies project belongs to the same company
   - System verifies project is active
   - System allows tasks without projects (standalone tasks)

3. **Task Creation**
   - System creates task record
   - System links task to selected project (if provided)
   - System links task to assigned employee (if provided)
   - Task is set to "open" status by default

4. **Task Available in Project**
   - Task appears in project's task list
   - Task contributes to project's task statistics
   - Task can be viewed when filtering by project

### Viewing Tasks by Project Flow

1. **User Requests Project Tasks**
   - User navigates to a specific project
   - User clicks "View Tasks" or requests project tasks endpoint
   - System queries all tasks linked to that project

2. **Task Filtering**
   - Tasks can be filtered by status (open, in_progress, closed)
   - Tasks can be filtered by priority (low, medium, high)
   - Results are paginated
   - System returns tasks with full details including project information

3. **Task List Display**
   - System shows all tasks for the project
   - Each task shows its status, priority, assignee, and due date
   - Tasks are sorted by creation date (newest first)

### Task Statistics in Projects Flow

1. **Project Statistics Calculation**
   - When viewing project details, system calculates task statistics
   - System counts total number of tasks in the project
   - System counts open tasks (status = open)
   - System counts in-progress tasks (status = in_progress)
   - System counts completed tasks (status = closed)

2. **Statistics Display**
   - Project details show task_count (total tasks)
   - Project details show open_task_count (open + in_progress)
   - Project details show completed_task_count (closed tasks)
   - Statistics update in real-time as tasks change status

### Filtering Tasks by Project Flow

1. **User Filters Tasks**
   - User navigates to task list
   - User selects a project from filter dropdown
   - User applies the filter

2. **System Applies Filter**
   - System queries tasks matching the selected project_id
   - System applies additional filters (status, priority) if provided
   - System returns only tasks belonging to that project
   - Results are paginated

3. **Standalone Tasks**
   - Tasks without projects (project_id = null) are not shown when filtering by project
   - To see all tasks including standalone, user removes project filter
   - Standalone tasks can still be managed independently

---

## User Workflows

### Employee Workflow

**Department Access:**
1. Employee logs into the system
2. Employee requests to see available departments
3. System returns only departments employee has been granted access to
4. Employee can view details of accessible departments
5. Employee cannot access departments without permission

**Project and Task Viewing:**
1. Employee can view all active projects in their company
2. Employee can view tasks assigned to them
3. Employee can filter tasks by project
4. Employee can view project details and task statistics
5. Employee can update tasks assigned to them (status, progress)

**Task Management:**
1. Employee receives task assignments (from admin)
2. Employee can view their assigned tasks
3. Employee can update task status (open → in_progress → closed)
4. Employee can view tasks organized by project
5. Employee cannot create or delete tasks

### Project Lead Workflow

**Project Management:**
1. Project lead logs into the system
2. Project lead navigates to "My Projects"
3. System shows all projects where user is the project lead
4. Project lead can view project details and statistics
5. Project lead can see all tasks in their projects

**Task Oversight:**
1. Project lead views project details
2. Project lead sees task statistics (total, open, completed)
3. Project lead can view all tasks in the project
4. Project lead can see task assignments and progress
5. Project lead has visibility into project progress

**Department Access:**
1. Project lead follows same department access rules as employees
2. Project lead can only access departments they've been granted access to
3. Project lead's project management is separate from department access

### Admin Workflow

**Department Management:**
1. Admin creates departments
2. Admin manages department information
3. Admin grants/revokes employee access to departments
4. Admin can view all departments in the company
5. Admin can see which users have access to which departments

**Project Management:**
1. Admin creates projects with client information
2. Admin assigns project leads
3. Admin updates project details and timelines
4. Admin can deactivate projects
5. Admin can view all projects and their statistics

**Task Management:**
1. Admin creates tasks
2. Admin assigns tasks to projects
3. Admin assigns tasks to employees
4. Admin can view all tasks across all projects
5. Admin can filter tasks by project, status, priority, assignee
6. Admin can update any task
7. Admin can close tasks

**Access Control:**
1. Admin manages department access permissions
2. Admin can grant access to multiple employees for multiple departments
3. Admin can revoke access when needed
4. Admin can view access reports (who has access to what)

---

## Admin Workflows

### Managing Department Access

**Granting Access:**
1. Admin identifies which employee needs access to which department
2. Admin uses the grant access endpoint
3. Admin provides user_id and department_id
4. System creates or reactivates access record
5. Employee immediately gains access

**Bulk Access Management:**
1. Admin can grant access to multiple employees for one department
2. Admin can grant access to one employee for multiple departments
3. Each grant operation is independent
4. System tracks who granted each access (for audit)

**Access Monitoring:**
1. Admin views department → sees all users with access
2. Admin views user → sees all departments user can access
3. Admin can identify access patterns and permissions
4. Admin can audit access grants

**Revoking Access:**
1. Admin identifies access to revoke
2. Admin uses the revoke access endpoint
3. System deactivates the access record
4. Employee immediately loses access
5. Access record is kept for audit (soft delete)

### Managing Projects

**Project Lifecycle:**
1. Admin creates project with initial details
2. Admin assigns project lead
3. Admin can update project details as needed
4. Admin can extend timeline (update target_date and number_of_days)
5. Admin can change project lead if needed
6. Admin deactivates project when complete

**Project Organization:**
1. Admin creates projects for different clients
2. Admin organizes projects by client or timeline
3. Admin can filter projects by lead or status
4. Admin tracks project progress through task statistics

**Task Assignment to Projects:**
1. Admin creates tasks
2. Admin assigns tasks to relevant projects
3. Admin can move tasks between projects (update project_id)
4. Admin can create standalone tasks (no project)
5. Admin organizes work through project-task structure

### Managing Tasks Within Projects

**Task Creation:**
1. Admin creates task with basic information
2. Admin selects project (optional but recommended)
3. Admin assigns task to employee
4. Admin sets priority and due date
5. Task appears in project's task list

**Task Organization:**
1. Admin views tasks by project
2. Admin sees project task statistics
3. Admin can identify which projects need attention
4. Admin can reassign tasks between projects
5. Admin can reassign tasks between employees

**Project Progress Tracking:**
1. Admin views project details
2. Admin sees task statistics (total, open, completed)
3. Admin can identify projects with many open tasks
4. Admin can identify projects nearing completion
5. Admin uses statistics to manage project timelines

---

## Additional Information

### Access Control Philosophy

The department access system follows a "deny by default" approach for employees:
- Employees start with NO department access
- Admins must explicitly grant access
- This ensures data privacy and proper access control
- Admins have full access by default for management purposes

### Project-Task Relationship

The project-task relationship is flexible:
- Tasks can exist without projects (standalone tasks)
- Projects can exist without tasks (new projects)
- Tasks can be moved between projects
- Tasks can be removed from projects (set project_id to null)
- This flexibility allows for various organizational structures

### Data Integrity

**Department Access:**
- Access records are never hard-deleted (only soft-deleted)
- System tracks who granted access (audit trail)
- Access records maintain company isolation
- Access is automatically checked on every department request

**Projects:**
- Projects maintain company isolation
- Project names must be unique within a company
- Project lead must belong to the same company
- Deactivated projects remain linked to tasks for historical data

**Tasks:**
- Tasks validate project belongs to same company
- Tasks can exist without projects
- Task-project relationship is optional but recommended
- Task statistics are calculated dynamically

### Performance Considerations

**Department Access:**
- Access checks are performed on every department request
- System uses indexed queries for fast access validation
- Access lists are cached in memory during request processing
- Bulk access operations are efficient

**Project Management:**
- Task statistics are calculated on-demand (not cached)
- Project lists support pagination for large datasets
- Project queries are optimized with proper indexing
- Task-project joins are efficient with foreign key indexes

### Security Considerations

**Access Control:**
- All access checks are performed server-side
- Client-side filtering is not trusted
- Access permissions are verified on every request
- Company isolation is enforced at database level

**Project Security:**
- Projects are isolated by company_id
- Users can only access projects in their company
- Project lead assignment is validated
- Project updates require admin privileges

**Task Security:**
- Tasks are isolated by company_id
- Task-project relationships are validated
- Task assignments are validated
- Employees can only update their own assigned tasks

---

## Summary

The system provides a comprehensive workflow for managing departments with access control and projects with task integration. Admins have full control over access permissions and project management, while employees have restricted access based on granted permissions. Projects serve as organizational containers for tasks, allowing better project tracking and management. The system maintains data integrity, security, and company isolation throughout all operations.

