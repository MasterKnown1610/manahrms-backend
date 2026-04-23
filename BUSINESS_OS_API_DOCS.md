# Business OS — API + Frontend UI Guide

Base URL: `{{BASE_URL}}/api/v1`  
Auth Header: `Authorization: Bearer <token>`  
All endpoints are tenant-scoped by the logged-in user's `company_id`.

---

## PART A — FRONTEND ARCHITECTURE (READ THIS FIRST)

### How the Frontend Makes Decisions

The frontend has **two independent axes** that control what a user sees:

```
AXIS 1: USER ROLE          →  admin  |  employee
AXIS 2: INDUSTRY TYPE      →  restaurant | temple | hospital | school | event | sme | generic
         +
         ENABLED MODULES   →  { "inventory": true, "crm": false, ... }
```

These two axes combine to produce the final UI. Read both axes on every login.

---

### Step 1 — Authentication (Get Token + Role)

```
POST /api/v1/auth/token
Body: { "username": "...", "password": "..." }
```

Response includes:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 5,
    "role": "admin",          ← "admin" or "employee"
    "full_name": "Ravi Kumar",
    "company_id": 23,
    "employee_id": null        ← null for admin, integer for employee users
  }
}
```

**Store in frontend state:**
- `token` → attach to all API calls
- `user.role` → controls sidebar items and action buttons
- `user.company_id` → for display only
- `user.employee_id` → null means the user is an admin (no employee profile)

---

### Step 2 — Load Company Profile (Get Industry + Modules)

**Immediately after login**, call:

```
GET /api/v1/company-profile
Authorization: Bearer <token>
```

Response:
```json
{
  "industry_type": "restaurant",
  "enabled_modules": {
    "employees": true,
    "attendance": true,
    "tasks": true,
    "projects": true,
    "leaves": true,
    "dashboard": true,
    "ai_chat": true,
    "chat": true,
    "meetings": true,
    "events": true,
    "calendar": true,
    "inventory": true,
    "assets": true,
    "crm": true,
    "booking": true,
    "billing_ops": true,
    "shifts": true,
    "donations": true
  },
  "custom_roles": ["chef", "waiter", "cashier"],
  "industry_settings": {}
}
```

**Store in frontend state:**
- `profile.industry_type` → controls labels and sidebar names
- `profile.enabled_modules` → dictionary of true/false per module
- `profile.custom_roles` → for dropdowns when creating employees

**If `enabled_modules` is `null`** → treat ALL modules as enabled (default open).

---

### Step 3 — Build the Sidebar

Use this decision table to build the navigation:

```
Show nav item IF:
  enabled_modules[key] === true   AND
  user satisfies role requirement for that module
```

---

## PART B — SIDEBAR VISIBILITY RULES

### Complete Module → Sidebar Mapping

| Module Key | Sidebar Label (Generic) | Admin | Employee | Notes |
|---|---|:---:|:---:|---|
| `dashboard` | Dashboard | ✅ | ✅ | Always first item |
| `employees` | Employees | ✅ | ❌ | Employee list is admin-only |
| `departments` | Departments | ✅ | ❌ | |
| `attendance` | Attendance | ✅ | ✅ | Admin sees all; employee sees own |
| `leaves` | Leaves | ✅ | ✅ | Admin approves; employee applies |
| `tasks` | Tasks | ✅ | ✅ | Admin sees all; employee sees assigned |
| `projects` | Projects | ✅ | ✅ | |
| `meetings` | Meetings | ✅ | ✅ | |
| `events` | Events | ✅ | ✅ | |
| `calendar` | Calendar | ✅ | ✅ | |
| `chat` | Team Chat | ✅ | ✅ | |
| `ai_chat` | AI Assistant | ✅ | ✅ | |
| `inventory` | Inventory | ✅ | ✅* | Employee: read + consume only |
| `assets` | Assets | ✅ | ✅* | Employee: view assigned assets only |
| `crm` | Clients / CRM | ✅ | ✅* | Employee: view + add only |
| `booking` | Bookings | ✅ | ✅ | Both can create bookings |
| `billing_ops` | Invoices | ✅ | ✅* | Employee: view + create drafts |
| `shifts` | Shifts | ✅ | ✅* | Employee: view own shift only |
| `donations` | Donations | ✅ | ✅ | Both can record donations |
| `subscriptions` | Billing & Plans | ✅ | ❌ | Admin only |

`✅*` = show to employee but with restricted actions (no delete, no admin-level edits)

---

### Industry-Specific Sidebar Labels

Apply these label overrides based on `industry_type`:

| Module Key | hospital | restaurant | temple | school | event | sme |
|---|---|---|---|---|---|---|
| `crm` | Patients | Customers | Devotees | Students | Clients | Customers |
| `booking` | Appointments | Reservations | Pooja Slots | Timetable | Event Bookings | Appointments |
| `inventory` | Medicines & Supplies | Ingredients | Prasad & Supplies | Stationery | Equipment | Inventory |
| `donations` | *(hide)* | *(hide)* | Donations | *(hide)* | *(hide)* | *(hide)* |
| `billing_ops` | Patient Bills | Bills | *(hide)* | Fee Invoices | Event Invoices | Invoices |

**Rule:** If industry-specific label is `*(hide)*` → do not show that module in sidebar regardless of `enabled_modules`.

---

## PART C — ROLE-BASED UI INSIDE EACH MODULE

### Global Rules

| UI Element | Admin | Employee |
|---|---|---|
| "Add / Create" buttons | ✅ Show | ❌ Hide (most modules) |
| "Edit / Update" buttons | ✅ Show | ❌ Hide |
| "Delete" buttons | ✅ Show | ❌ Hide always |
| "Approve / Reject" buttons | ✅ Show | ❌ Hide |
| Export / Reports | ✅ Show | ❌ Hide |
| Filter: "All employees" | ✅ Show | ❌ Hide (see own data only) |

---

### Module: Dashboard

| Section | Admin | Employee |
|---|---|---|
| Total employees count | ✅ | ❌ |
| Present today count | ✅ | ❌ |
| Pending leave approvals | ✅ | ❌ |
| My attendance today | ❌ | ✅ |
| My tasks due today | ❌ | ✅ |
| My shift today | ❌ | ✅ (if shifts module enabled) |
| Low stock alerts | ✅ | ❌ |
| Donation summary | ✅ | ❌ (if temple) |
| Open invoices count | ✅ | ❌ |

---

### Module: Employees

| Action | Admin | Employee |
|---|---|---|
| View full employee list | ✅ | ❌ (redirect to "My Profile") |
| View single employee | ✅ | ✅ (own profile only) |
| Create employee | ✅ | ❌ |
| Edit employee | ✅ | ❌ |
| Delete employee | ✅ | ❌ |
| View salary | ✅ | ❌ |
| Download employee report | ✅ | ❌ |

---

### Module: Attendance

| Action | Admin | Employee |
|---|---|---|
| View all employee attendance | ✅ | ❌ |
| View own attendance | ✅ | ✅ |
| Punch In / Out button | ❌ (admin rarely needs) | ✅ |
| Mark attendance for others | ✅ | ❌ |
| Export attendance report | ✅ | ❌ |

---

### Module: Leaves

| Action | Admin | Employee |
|---|---|---|
| View all leave requests | ✅ | ❌ |
| View own leave requests | ✅ | ✅ |
| Apply for leave | ❌ | ✅ |
| Approve / Reject button | ✅ | ❌ |
| Leave balance (all) | ✅ | ❌ |
| Leave balance (own) | ✅ | ✅ |

---

### Module: Inventory

| Action | Admin | Employee |
|---|---|---|
| View item list | ✅ | ✅ |
| Add new item | ✅ | ❌ |
| Edit item details | ✅ | ❌ |
| Delete item | ✅ | ❌ |
| Add stock (stock_in) | ✅ | ❌ |
| Consume stock (stock_out) | ✅ | ✅ |
| View low-stock alerts | ✅ | ✅ |
| Manage categories | ✅ | ❌ |

**Industry label for "Stock Out" button:**

| Industry | Button Label |
|---|---|
| restaurant | Use in Kitchen |
| hospital | Dispense |
| temple | Use for Pooja |
| school | Issue to Student |
| generic | Consume |

---

### Module: Assets

| Action | Admin | Employee |
|---|---|---|
| View all assets | ✅ | ❌ |
| View own assigned assets | ❌ | ✅ |
| Add asset | ✅ | ❌ |
| Edit asset | ✅ | ❌ |
| Assign to employee | ✅ | ❌ |
| Mark returned | ✅ | ❌ |
| Log maintenance | ✅ | ❌ |

---

### Module: CRM (Clients / Patients / Customers)

| Action | Admin | Employee |
|---|---|---|
| View client list | ✅ | ✅ |
| Add client | ✅ | ✅ |
| Edit client | ✅ | ✅ |
| Delete client | ✅ | ❌ |
| View interaction history | ✅ | ✅ |
| Log interaction | ✅ | ✅ |

**Industry-specific field labels:**

| Field | hospital | restaurant | temple |
|---|---|---|---|
| `name` | Patient Name | Customer Name | Devotee Name |
| `industry_label` | patient | customer | devotee |
| `custom_attributes.blood_group` | Show | Hide | Hide |
| `date_of_birth` | Show | Hide | Show |
| `organization_name` | Hospital/Referral | Corporate Client | Organization |

---

### Module: Booking (Appointments / Reservations)

| Action | Admin | Employee |
|---|---|---|
| View all bookings | ✅ | ✅ |
| Create booking | ✅ | ✅ |
| Edit booking | ✅ | ✅ (own created) |
| Cancel booking | ✅ | ✅ |
| Manage resources (rooms/tables) | ✅ | ❌ |
| View resource availability calendar | ✅ | ✅ |

**Industry-specific form labels:**

| Field | hospital | restaurant | temple | event |
|---|---|---|---|---|
| Page title | Appointments | Table Reservations | Pooja Booking | Event Booking |
| `title` | Consultation | Reservation | Pooja Slot | Event Name |
| `employee_id` | Assign Doctor | Assign Waiter | Assign Priest | Assign Coordinator |
| `client_id` | Patient | Customer | Devotee | Client |
| `resource_id` | OPD Room | Table | Sanctum Slot | Venue |

---

### Module: Billing / Invoices

| Action | Admin | Employee |
|---|---|---|
| View all invoices | ✅ | ✅ |
| Create draft invoice | ✅ | ✅ |
| Edit invoice | ✅ | ✅ |
| Mark as Sent | ✅ | ✅ |
| Mark as Paid | ✅ | ❌ |
| Cancel invoice | ✅ | ❌ |
| Delete invoice | ❌ (use cancel) | ❌ |

---

### Module: Shifts

| Action | Admin | Employee |
|---|---|---|
| View all shifts | ✅ | ✅ (view only) |
| Create shift | ✅ | ❌ |
| Edit shift | ✅ | ❌ |
| View all assignments | ✅ | ❌ |
| My current shift | ❌ | ✅ (show on dashboard + profile) |
| Assign employee to shift | ✅ | ❌ |

---

### Module: Donations (Temple / Charitable)

| Action | Admin | Employee |
|---|---|---|
| View donation list | ✅ | ✅ |
| Record donation | ✅ | ✅ |
| Edit donation | ✅ | ❌ |
| View summary (total collected) | ✅ | ✅ |
| Export receipt | ✅ | ✅ |

---

## PART D — STARTUP FLOW (Frontend Implementation)

```
1. User enters username + password
   → POST /auth/token
   → Store: token, user.role, user.id, user.employee_id

2. Immediately (parallel calls):
   → GET /company-profile     (get industry_type + enabled_modules)
   → GET /dashboard           (pre-load stats)

3. Build sidebar:
   For each module in SIDEBAR_CONFIG:
     show = (enabled_modules[module.key] !== false)   // default true if null
          && roleAllowed(user.role, module.key)
          && !industryHides(industry_type, module.key)
     if (show) → add to sidebar with industryLabel(industry_type, module.key)

4. Set global context:
   - industryType  → used by all pages for label overrides
   - userRole      → used by all pages for button visibility
   - enabledModules → used to guard route access

5. On every page render:
   - Check enabledModules[currentModule] before rendering
   - If false or missing → redirect to /dashboard with "Module not enabled" toast

6. On every action button:
   - Check user.role === 'admin' before showing Edit/Delete/Approve buttons
   - Never rely on 403 from API to hide buttons — check role locally first
```

---

## PART E — COMPLETE SIDEBAR CONFIG (Copy-Paste Ready)

```json
[
  {
    "key": "dashboard",
    "icon": "LayoutDashboard",
    "defaultLabel": "Dashboard",
    "path": "/dashboard",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "employees",
    "icon": "Users",
    "defaultLabel": "Employees",
    "path": "/employees",
    "roles": ["admin"],
    "industryLabels": {
      "hospital": "Staff Directory",
      "restaurant": "Staff",
      "temple": "Staff & Volunteers",
      "school": "Staff"
    }
  },
  {
    "key": "departments",
    "icon": "Building2",
    "defaultLabel": "Departments",
    "path": "/departments",
    "roles": ["admin"],
    "industryLabels": {
      "hospital": "Wards & Departments",
      "restaurant": "Sections",
      "temple": "Departments",
      "school": "Departments"
    }
  },
  {
    "key": "attendance",
    "icon": "CalendarCheck",
    "defaultLabel": "Attendance",
    "path": "/attendance",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "leaves",
    "icon": "CalendarOff",
    "defaultLabel": "Leaves",
    "path": "/leaves",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "shifts",
    "icon": "Clock",
    "defaultLabel": "Shifts",
    "path": "/shifts",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Duty Roster",
      "restaurant": "Shift Schedule"
    }
  },
  {
    "key": "tasks",
    "icon": "CheckSquare",
    "defaultLabel": "Tasks",
    "path": "/tasks",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Tasks",
      "restaurant": "Kitchen Tasks",
      "temple": "Seva Tasks"
    }
  },
  {
    "key": "projects",
    "icon": "FolderKanban",
    "defaultLabel": "Projects",
    "path": "/projects",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "event": "Events & Projects",
      "school": "Academic Projects"
    }
  },
  {
    "key": "inventory",
    "icon": "Package",
    "defaultLabel": "Inventory",
    "path": "/inventory",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Medicines & Supplies",
      "restaurant": "Ingredients & Stock",
      "temple": "Prasad & Supplies",
      "school": "Stationery & Supplies",
      "event": "Equipment & Materials"
    }
  },
  {
    "key": "assets",
    "icon": "Laptop",
    "defaultLabel": "Assets",
    "path": "/assets",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Medical Equipment",
      "restaurant": "Kitchen Equipment",
      "event": "AV & Equipment"
    }
  },
  {
    "key": "crm",
    "icon": "ContactRound",
    "defaultLabel": "Clients",
    "path": "/crm",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Patients",
      "restaurant": "Customers",
      "temple": "Devotees",
      "school": "Students",
      "event": "Clients",
      "sme": "Customers"
    }
  },
  {
    "key": "booking",
    "icon": "CalendarPlus",
    "defaultLabel": "Bookings",
    "path": "/bookings",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Appointments",
      "restaurant": "Table Reservations",
      "temple": "Pooja Slots",
      "school": "Class Schedule",
      "event": "Event Bookings"
    }
  },
  {
    "key": "billing_ops",
    "icon": "FileText",
    "defaultLabel": "Invoices",
    "path": "/billing",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Patient Bills",
      "restaurant": "Bills",
      "school": "Fee Invoices",
      "event": "Event Invoices",
      "sme": "Invoices"
    },
    "hideForIndustry": ["temple"]
  },
  {
    "key": "donations",
    "icon": "HeartHandshake",
    "defaultLabel": "Donations",
    "path": "/donations",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "temple": "Donations & Receipts"
    },
    "showOnlyForIndustry": ["temple", "event", "school"]
  },
  {
    "key": "meetings",
    "icon": "Video",
    "defaultLabel": "Meetings",
    "path": "/meetings",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "events",
    "icon": "CalendarDays",
    "defaultLabel": "Events",
    "path": "/events",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "calendar",
    "icon": "Calendar",
    "defaultLabel": "Calendar",
    "path": "/calendar",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "chat",
    "icon": "MessageSquare",
    "defaultLabel": "Team Chat",
    "path": "/chat",
    "roles": ["admin", "employee"],
    "industryLabels": {}
  },
  {
    "key": "ai_chat",
    "icon": "Bot",
    "defaultLabel": "AI Assistant",
    "path": "/ai-chat",
    "roles": ["admin", "employee"],
    "industryLabels": {
      "hospital": "Hospital AI",
      "restaurant": "Kitchen AI",
      "temple": "Temple AI"
    }
  },
  {
    "key": "subscriptions",
    "icon": "CreditCard",
    "defaultLabel": "Billing & Plans",
    "path": "/subscriptions",
    "roles": ["admin"],
    "industryLabels": {}
  }
]
```

---

## PART F — MODULE GUARD (Frontend Pseudocode)

```js
// Call this once after login — store result in global context
async function loadAppContext(token) {
  const [profile] = await Promise.all([
    fetch('/api/v1/company-profile', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
  ]);

  return {
    industryType: profile.industry_type ?? 'generic',
    enabledModules: profile.enabled_modules ?? null,  // null = all enabled
    customRoles: profile.custom_roles ?? [],
  };
}

// Use this to check if a module is accessible
function isModuleEnabled(moduleKey, enabledModules) {
  if (!enabledModules) return true;           // null = all on
  return enabledModules[moduleKey] === true;
}

// Use this to check if user can perform admin actions
function canAdminAction(userRole) {
  return userRole === 'admin';
}

// Build final sidebar items
function buildSidebar(sidebarConfig, userRole, industryType, enabledModules) {
  return sidebarConfig
    .filter(item => {
      // 1. Role check
      if (!item.roles.includes(userRole)) return false;
      // 2. Module enabled check
      if (!isModuleEnabled(item.key, enabledModules)) return false;
      // 3. Industry hide rule
      if (item.hideForIndustry?.includes(industryType)) return false;
      // 4. Industry show-only rule
      if (item.showOnlyForIndustry && !item.showOnlyForIndustry.includes(industryType)) return false;
      return true;
    })
    .map(item => ({
      ...item,
      label: item.industryLabels[industryType] ?? item.defaultLabel,
    }));
}

// Use this on every page to guard access
function guardRoute(moduleKey, enabledModules, userRole, requiredRole = null) {
  if (!isModuleEnabled(moduleKey, enabledModules)) {
    redirect('/dashboard');
    toast('This module is not enabled for your account');
    return false;
  }
  if (requiredRole && userRole !== requiredRole) {
    redirect('/dashboard');
    toast('You do not have permission to access this page');
    return false;
  }
  return true;
}
```

---

## PART G — HTTP 403 HANDLING

When any API call returns `403 Forbidden`, the frontend should:

1. Show a **non-intrusive toast**: `"You don't have permission to perform this action"`
2. **Do NOT redirect** to login — 403 is a permission error, not an auth error
3. **Revert any optimistic UI** updates
4. **Do NOT retry** the request

When any API call returns `401 Unauthorized`:

1. **Clear the stored token**
2. **Redirect to login page**
3. Show toast: `"Session expired. Please log in again."`

---

## PART H — AI ASSISTANT (Industry-Aware)

The AI automatically knows the industry type from the company profile. No special setup needed on frontend.

**AI chat page:**
- Same UI for all industries
- Just change the **placeholder text** based on industry:

| Industry | Placeholder |
|---|---|
| restaurant | "Ask about ingredients, orders, staff shifts..." |
| hospital | "Ask about medicines, patient appointments, staff..." |
| temple | "Ask about donations, pooja schedules, inventory..." |
| school | "Ask about timetable, staff, supplies..." |
| event | "Ask about bookings, clients, equipment..." |
| generic | "Ask anything about your business..." |

The AI can answer questions **and take actions** (with confirmation):
- Admin: create employees, manage inventory, approve leaves, create bookings
- Employee: punch in/out, check own tasks, view inventory, apply for leave

---

## PART I — API REFERENCE (All Endpoints)

### Authentication

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| POST | `/auth/token` | None | — |
| POST | `/auth/register` | None | — |
| POST | `/auth/logout` | Bearer | any |

### Company Profile

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/company-profile` | Bearer | any |
| PUT | `/company-profile` | Bearer | admin |

### Employees

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/employees` | Bearer | admin |
| POST | `/employees/create` | Bearer | admin |
| GET | `/employees/{id}` | Bearer | any |
| PATCH | `/employees/{id}` | Bearer | admin |
| DELETE | `/employees/{id}` | Bearer | admin |

### Departments

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/departments` | Bearer | any |
| POST | `/departments` | Bearer | admin |
| PATCH | `/departments/{id}` | Bearer | admin |
| DELETE | `/departments/{id}` | Bearer | admin |

### Attendance

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| POST | `/attendance/punch-in` | Bearer | employee |
| POST | `/attendance/punch-out` | Bearer | employee |
| GET | `/attendance` | Bearer | admin |
| GET | `/attendance/my` | Bearer | employee |

### Leaves

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| POST | `/leaves/apply` | Bearer | employee |
| GET | `/leaves` | Bearer | admin |
| GET | `/leaves/my` | Bearer | employee |
| POST | `/leaves/{id}/approve` | Bearer | admin |
| POST | `/leaves/{id}/reject` | Bearer | admin |

### Tasks

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/tasks` | Bearer | admin |
| POST | `/tasks` | Bearer | admin |
| GET | `/tasks/my` | Bearer | employee |
| PATCH | `/tasks/{id}` | Bearer | admin |
| PATCH | `/tasks/{id}/status` | Bearer | employee |

### Inventory

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/inventory/categories` | Bearer | any |
| POST | `/inventory/categories` | Bearer | admin |
| PATCH | `/inventory/categories/{id}` | Bearer | admin |
| GET | `/inventory/items` | Bearer | any |
| POST | `/inventory/items` | Bearer | admin |
| GET | `/inventory/items/{id}` | Bearer | any |
| PATCH | `/inventory/items/{id}` | Bearer | admin |
| DELETE | `/inventory/items/{id}` | Bearer | admin |
| POST | `/inventory/transactions` | Bearer | any (consume) |
| GET | `/inventory/alerts/low-stock` | Bearer | any |

### Assets

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/assets` | Bearer | admin |
| POST | `/assets` | Bearer | admin |
| GET | `/assets/{id}` | Bearer | admin |
| PATCH | `/assets/{id}` | Bearer | admin |
| DELETE | `/assets/{id}` | Bearer | admin |
| GET | `/assets/assignments/list` | Bearer | any |
| POST | `/assets/assignments` | Bearer | admin |
| POST | `/assets/assignments/{id}/return` | Bearer | admin |
| POST | `/assets/maintenance` | Bearer | admin |

### CRM

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/crm/clients` | Bearer | any |
| POST | `/crm/clients` | Bearer | any |
| GET | `/crm/clients/{id}` | Bearer | any |
| PATCH | `/crm/clients/{id}` | Bearer | any |
| DELETE | `/crm/clients/{id}` | Bearer | admin |
| GET | `/crm/clients/{id}/interactions` | Bearer | any |
| POST | `/crm/interactions` | Bearer | any |

### Bookings

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/bookings/resources` | Bearer | any |
| POST | `/bookings/resources` | Bearer | admin |
| PATCH | `/bookings/resources/{id}` | Bearer | admin |
| GET | `/bookings` | Bearer | any |
| POST | `/bookings` | Bearer | any |
| GET | `/bookings/{id}` | Bearer | any |
| PATCH | `/bookings/{id}` | Bearer | any |
| POST | `/bookings/{id}/cancel` | Bearer | any |

### Billing Operations

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/billing/invoices` | Bearer | any |
| POST | `/billing/invoices` | Bearer | any |
| GET | `/billing/invoices/{id}` | Bearer | any |
| PATCH | `/billing/invoices/{id}` | Bearer | any |
| POST | `/billing/invoices/{id}/mark-paid` | Bearer | admin |

### Shifts

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/shifts` | Bearer | any |
| POST | `/shifts` | Bearer | admin |
| PATCH | `/shifts/{id}` | Bearer | admin |
| GET | `/shifts/assignments` | Bearer | admin |
| POST | `/shifts/assignments` | Bearer | admin |
| GET | `/shifts/assignments/my-shift` | Bearer | employee |

### Donations

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/donations` | Bearer | any |
| POST | `/donations` | Bearer | any |
| GET | `/donations/summary` | Bearer | any |
| GET | `/donations/{id}` | Bearer | any |
| PATCH | `/donations/{id}` | Bearer | admin |

### Meetings / Events / Calendar / Chat

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/meetings` | Bearer | any |
| POST | `/meetings` | Bearer | admin |
| GET | `/events` | Bearer | any |
| POST | `/events` | Bearer | admin |
| GET | `/calendar` | Bearer | any |
| GET | `/chat/rooms` | Bearer | any |

### AI Chat

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| POST | `/ai-chat/ask` | Bearer | any |
| POST | `/ai-chat/ask/stream` | Bearer | any (SSE) |
| GET | `/ai-chat/usage/me` | Bearer | any |
| GET | `/ai-chat/usage/users` | Bearer | admin |

### Subscriptions

| Method | Endpoint | Auth | Role |
|---|---|---|---|
| GET | `/subscriptions/plans` | Bearer | admin |
| GET | `/subscriptions/current` | Bearer | admin |
| POST | `/subscriptions/purchase` | Bearer | admin |
| POST | `/subscriptions/upgrade` | Bearer | admin |

---

## PART J — ENUM VALUES (Frontend Dropdowns)

```js
const ENUMS = {
  industry_type:      ['hospital', 'restaurant', 'temple', 'school', 'event', 'sme', 'generic'],
  item_type:          ['consumable', 'asset', 'service'],
  transaction_type:   ['stock_in', 'stock_out', 'adjustment', 'return'],
  asset_status:       ['available', 'assigned', 'under_maintenance', 'retired'],
  client_type:        ['individual', 'organization'],
  interaction_type:   ['call', 'visit', 'email', 'note', 'appointment'],
  booking_status:     ['pending', 'confirmed', 'cancelled', 'completed', 'no_show'],
  invoice_status:     ['draft', 'sent', 'paid', 'overdue', 'cancelled'],
  donation_mode:      ['cash', 'online', 'cheque', 'demand_draft', 'upi'],
  user_role:          ['admin', 'employee'],
};
```

---

## PART K — ERROR HANDLING

| HTTP Code | Meaning | Frontend Action |
|---|---|---|
| `200` | Success | Render data |
| `201` | Created | Show success toast, refresh list |
| `204` | Deleted | Show success toast, remove from list |
| `400` | Bad Request | Show field-level error from `detail` |
| `401` | Unauthorized | Clear token → redirect to login |
| `402` | Seat limit | Show upgrade modal |
| `403` | Forbidden | Show toast "No permission", do NOT redirect |
| `404` | Not Found | Show "Not found" page or toast |
| `409` | Conflict | Show specific conflict message (e.g., booking overlap) |
| `422` | Validation Error | Show field errors from `detail[].msg` |
| `500` | Server Error | Show generic error toast |

### Extracting error messages:
```js
async function apiCall(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    // FastAPI validation errors have: err.detail (array or string)
    const message = Array.isArray(err.detail)
      ? err.detail.map(e => e.msg).join(', ')
      : err.detail ?? 'Something went wrong';
    throw new Error(message);
  }
  return res.json();
}
```

---

*Last updated: 2026-04-23 | ManaHRMS Business OS v2*
