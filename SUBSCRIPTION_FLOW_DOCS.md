# ManaHRMS Subscription System — Complete Guide

> This document explains how the subscription system works end-to-end:
> how plans are structured, what every API does, how billing works,
> how AI credits work, and what happens at each lifecycle stage.

---

## Table of Contents

1. [How Subscriptions Work — Plain English](#1-how-subscriptions-work--plain-english)
2. [The Three Plans](#2-the-three-plans)
3. [Key Concepts](#3-key-concepts)
4. [Subscription Lifecycle](#4-subscription-lifecycle)
5. [Complete API Reference](#5-complete-api-reference)
6. [AI Credits System](#6-ai-credits-system)
7. [What Blocks the App When Subscription Expires](#7-what-blocks-the-app-when-subscription-expires)
8. [Frontend — What to Build](#8-frontend--what-to-build)
9. [Error Reference](#9-error-reference)
10. [Flow Diagrams](#10-flow-diagrams)

---

## 1. How Subscriptions Work — Plain English

1. A company **registers** on ManaHRMS → they have no subscription yet.
2. The admin goes to the Subscription page and **picks a plan** (Starter / Growth / Scale).
3. The admin chooses **monthly or yearly billing** and how many **seats** (= how many employees they want to have).
4. They confirm → `POST /subscriptions/create` is called → a subscription record is created instantly with status `active`.
5. The subscription has a **period** — 30 days (monthly) or 365 days (yearly) — counted from today.
6. When the period ends, the subscription status becomes `expired` and **access is blocked** until they renew.
7. To **renew or switch plans**, the admin calls `PATCH /subscriptions/upgrade` with the new plan / billing cycle / seat count. This starts a fresh period immediately.
8. Each plan gives the company a **monthly AI query limit**. When it runs out, they can buy an **AI add-on pack** to top up.

---

## 2. The Three Plans

| | Starter | Growth | Scale |
|---|---|---|---|
| **Monthly price / user** | ₹49 | ₹39 | ₹29 |
| **Yearly price / user** | ₹470 | ₹374.40 | ₹278.40 |
| **Minimum seats** | 1 | 10 | 25 |
| **AI queries / month** | 300 | 800 | 2,000 |
| **Chat module** | ✗ | ✓ | ✓ |

**Yearly billing saves ~20%** compared to monthly.

### How price is calculated

```
billable_seats = max(requested_seats, plan_minimum_seats)
monthly_cost   = billable_seats × price_per_user
```

**Example:** Growth plan, 8 seats requested
- `billable_seats = max(8, 10) = 10` (minimum enforced)
- `monthly_cost = 10 × ₹39 = ₹390/month`

---

## 3. Key Concepts

### Seats vs Employees

| Term | Meaning |
|---|---|
| `seat_count` | How many seats the admin **requested** |
| `billable_seats` | `max(seat_count, plan.minimum_seats)` — what they actually **pay for** |
| `employees_used` | How many employees currently exist in the company |

If `employees_used >= billable_seats`, **adding a new employee is blocked** until the admin buys more seats (`PATCH /update-seats`) or upgrades the plan.

### Billing Cycle

- `monthly` → period lasts 30 days, price = `price_per_user_monthly`
- `yearly` → period lasts 365 days, price = `price_per_user_yearly`

### Subscription Statuses

| Status | What it means |
|---|---|
| `active` | Subscription is running, full access |
| `past_due` | Payment was missed (reserved for future Razorpay webhook integration) |
| `cancelled` | Admin cancelled; may still have access until `current_period_end` |
| `expired` | Period ended; **app access is blocked** |
| `trial` | Reserved for future trial feature |

---

## 4. Subscription Lifecycle

```
[Company registers]
        │
        ▼
[No subscription — limited access]
        │
  Admin calls POST /create
        │
        ▼
[status: active]  ←──────────────────────────────────────────┐
        │                                                     │
        │  Period ends (30 or 365 days)                       │
        │                                                     │
        ▼                                                     │
[status: expired — app blocked]          Admin calls PATCH /upgrade
        │                                 (renew or change plan)
        └──────────────────────────────────────────────────────┘

                    OR

[status: active]
        │
  Admin calls POST /cancel  (cancel_at_period_end=true)
        │
        ▼
[status: active, cancel_at_period_end=true]
  Still works until period_end
        │
  Period ends
        │
        ▼
[status: cancelled — app blocked]
        │
  Admin calls PATCH /upgrade to reactivate
        │
        ▼
[status: active — fresh period starts]
```

---

## 5. Complete API Reference

Base URL: `https://<domain>/api/v1/subscriptions`

All endpoints require: `Authorization: Bearer <token>`

---

### 5.1 Get All Plans

```
GET /subscriptions/plans
```

**Auth:** None required (public)

**Response `200`:**
```json
[
  {
    "id": "9ed7ae7c-6cb6-43be-bc84-f9cea22d1dbb",
    "name": "Starter",
    "plan_key": "starter",
    "price_per_user_monthly": "49.00",
    "price_per_user_yearly": "470.00",
    "minimum_seats": 1,
    "ai_queries_limit": 300,
    "features": { "employees": true, "attendance": true, "chat": false, ... },
    "is_active": true
  },
  {
    "id": "...",
    "name": "Growth",
    "plan_key": "growth",
    "price_per_user_monthly": "39.00",
    "price_per_user_yearly": "374.40",
    "minimum_seats": 10,
    "ai_queries_limit": 800,
    "features": { "employees": true, "attendance": true, "chat": true, ... },
    "is_active": true
  },
  {
    "id": "...",
    "name": "Scale",
    "plan_key": "scale",
    "price_per_user_monthly": "29.00",
    "price_per_user_yearly": "278.40",
    "minimum_seats": 25,
    "ai_queries_limit": 2000,
    "features": { ... },
    "is_active": true
  }
]
```

---

### 5.2 Create Subscription (first time only)

```
POST /subscriptions/create
```

**Auth:** Admin only

**Use this only when the company has NO subscription at all.**
If they already have one (even expired/cancelled), use `PATCH /upgrade` instead.

**Request body:**
```json
{
  "plan_id": "9ed7ae7c-6cb6-43be-bc84-f9cea22d1dbb",
  "billing_cycle": "monthly",
  "seat_count": 10
}
```

| Field | Type | Required |
|---|---|---|
| `plan_id` | UUID string | Yes |
| `billing_cycle` | `"monthly"` or `"yearly"` | Yes |
| `seat_count` | number ≥ 1 | Yes |

**Response `201`:** `SubscriptionResponse` (see shape below)

**Error `400` — already has a subscription:**
```json
{
  "success": false,
  "message": "Company already has an active subscription",
  "error_code": "SUBSCRIPTION_EXISTS"
}
```
→ **If you get this error, use `PATCH /upgrade` instead.**

---

### 5.3 Upgrade / Change Plan ← NEW (this was missing before)

```
PATCH /subscriptions/upgrade
```

**Auth:** Admin only

**Use this to:**
- Switch from Starter → Growth → Scale (upgrade)
- Switch from Scale → Growth → Starter (downgrade)
- Change monthly ↔ yearly billing
- Change seat count
- Renew an expired or cancelled subscription

**Request body:**
```json
{
  "plan_id": "<new-plan-uuid>",
  "billing_cycle": "yearly",
  "seat_count": 25
}
```

**What happens internally:**
1. Finds the company's existing subscription (any status)
2. Swaps the plan, billing cycle, seat count, price
3. Sets status back to `active`
4. Starts a fresh billing period from today (30 or 365 days)
5. Updates the AI query limit for the current month to match the new plan
6. Clears any cancellation flags

**Response `200`:** `SubscriptionResponse`

**Error `404` — no subscription exists yet:**
```json
{
  "success": false,
  "message": "No subscription found for this company. Use /create to start one.",
  "error_code": "SUBSCRIPTION_NOT_FOUND"
}
```

---

### 5.4 Update Seats Only

```
PATCH /subscriptions/update-seats
```

**Auth:** Admin only

**Use this when** the plan stays the same but you want to change the number of seats.

**Request body:**
```json
{ "seat_count": 20 }
```

**Response `200`:** `SubscriptionResponse`

---

### 5.5 Cancel Subscription

```
POST /subscriptions/cancel?cancel_at_period_end=true
```

**Auth:** Admin only

| `cancel_at_period_end` | Effect |
|---|---|
| `true` (default) | Access continues until `current_period_end`, then stops |
| `false` | Subscription is cancelled immediately right now |

**Response `200`:**
```json
{ "message": "Subscription will be cancelled at period end", "success": true }
```

---

### 5.6 Get Current Subscription (Dashboard)

```
GET /subscriptions/current
```

**Auth:** Any authenticated user

**Response `200`:**
```json
{
  "plan": "Growth",
  "plan_key": "growth",
  "employees_used": 8,
  "billable_seats": 10,
  "price_per_user": "39.00",
  "monthly_cost": "390.00",
  "billing_cycle": "monthly",
  "ai_usage": 142,
  "ai_limit": 800,
  "ai_remaining": 658,
  "next_billing_date": "2026-05-12T09:00:00",
  "status": "active"
}
```

| Field | Meaning |
|---|---|
| `employees_used` | Number of employees currently in the company |
| `billable_seats` | Seats being paid for |
| `ai_usage` | AI queries used **this month** |
| `ai_limit` | Total limit this month (plan base + add-ons purchased) |
| `ai_remaining` | `ai_limit - ai_usage` |
| `next_billing_date` | When the current period ends |

---

### SubscriptionResponse shape (used by create/upgrade/update-seats)

```json
{
  "id": "uuid-string",
  "company_id": 5,
  "plan": {
    "id": "uuid-string",
    "name": "Growth",
    "plan_key": "growth",
    "price_per_user_monthly": "39.00",
    "price_per_user_yearly": "374.40",
    "minimum_seats": 10,
    "ai_queries_limit": 800,
    "features": { ... },
    "is_active": true
  },
  "billing_cycle": "monthly",
  "seat_count": 12,
  "billable_seats": 12,
  "price_per_user": "39.00",
  "monthly_cost": "468.00",
  "status": "active",
  "current_period_start": "2026-04-12T09:00:00",
  "current_period_end": "2026-05-12T09:00:00",
  "cancel_at_period_end": false,
  "razorpay_subscription_id": null,
  "created_at": "2026-04-12T09:00:00",
  "updated_at": "2026-04-12T09:00:00"
}
```

---

## 6. AI Credits System

### How AI queries are counted

- Every time a user sends a message to the AI assistant, **1 query is consumed**.
- Queries reset to 0 on the **1st of every month**.
- The base monthly limit comes from the plan (`ai_queries_limit`).
- Admins can **buy add-on packs** to get more queries for the current month.

### Add-on Packs

| Pack | Queries Added | Price |
|---|---|---|
| `AI_1000_PACK` | +1,000 queries | ₹199 |
| `AI_5000_PACK` | +5,000 queries | ₹799 |

Add-ons apply to the **current month only**. They don't roll over.

### Step 1 — Create a Razorpay payment order

```
POST /subscriptions/ai-addon/order
```

**Request body:**
```json
{ "addon_type": "AI_1000_PACK" }
```

**Response:**
```json
{
  "order_id": "order_ABC123",
  "amount": 199.00,
  "currency": "INR",
  "key": "rzp_live_xxxx"
}
```

Use this to open the **Razorpay payment popup** on the frontend.

### Step 2 — Verify payment and apply

After the user completes payment, Razorpay returns `payment_id`, `order_id`, `signature`.

```
POST /subscriptions/ai-addon/verify?payment_id=pay_xxx&order_id=order_xxx&signature=xxx&addon_type=AI_1000_PACK
```

**Response:**
```json
{ "message": "AI add-on purchased successfully. 1000 queries added.", "success": true }
```

---

## 7. What Blocks the App When Subscription Expires

When the `current_period_end` has passed and status is `expired` or `cancelled`, every API call (except subscription endpoints) returns:

```
HTTP 403
{
  "success": false,
  "message": "Your subscription has expired. Please renew to continue using the service.",
  "error_code": "SUBSCRIPTION_EXPIRED"
}
```

**Exceptions — these still work with an expired subscription:**
- `GET /subscriptions/plans` — so they can pick a new plan
- `POST /subscriptions/create` — to create (if they never had one)
- `PATCH /subscriptions/upgrade` — **to renew or change plan**
- `GET /subscriptions/current` — to see their status
- `POST /auth/login` — so they can log in
- `POST /auth/forgot-password` / `POST /auth/reset-password`

---

## 8. Frontend — What to Build

### Decision Tree — which endpoint to call

```
Does the company have any subscription record?
│
├── NO  → call POST /subscriptions/create
│
└── YES → call PATCH /subscriptions/upgrade
          (works for renew, change plan, change seats, change billing)
```

**How to know if they have a subscription:**  
Call `GET /subscriptions/current`. If `status` is `null`, they have none.

---

### Subscription Page UI

#### Section 1 — Current Plan Card
Show from `GET /subscriptions/current`:
```
Plan: Growth        Status: ● Active
Seats: 8 / 10       Next renewal: 12 May 2026
Monthly cost: ₹390  Billing: Monthly
```

Status badge colors:
- `active` → green
- `past_due` → orange / yellow
- `cancelled` → red (show "Access until {date}")
- `expired` → red (show "Renew now" CTA)

#### Section 2 — AI Usage Bar
```
AI Queries this month
████████░░░░░░░░  142 / 800 used
                  658 remaining

[Buy +1000 queries — ₹199]  [Buy +5000 queries — ₹799]
```

#### Section 3 — Plan Comparison (for upgrade/downgrade)
Show all 3 plans side by side from `GET /subscriptions/plans`.
Highlight the current plan.

Each plan card has:
- Name, price/user/month, price/user/year
- Feature list
- "Switch to this plan" button (disabled on current plan)

Clicking "Switch to this plan" opens a modal:

```
Change to Growth Plan

Billing cycle:  ○ Monthly (₹39/user)   ○ Yearly (₹374.40/user)
Seats:          [  12  ]  (minimum: 10)

Cost preview:
  Billable seats: 12
  Price per seat: ₹39/month
  Total: ₹468/month

[Confirm Change]  [Cancel]
```

On confirm → call `PATCH /subscriptions/upgrade` with `{ plan_id, billing_cycle, seat_count }`.

#### Section 4 — Danger Zone
```
[Update seat count]   → PATCH /update-seats
[Cancel subscription] → POST /cancel?cancel_at_period_end=true
```

---

### Expired Subscription Screen

When any API call returns `error_code: "SUBSCRIPTION_EXPIRED"`, show a **full-page blocker**:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ⚠️  Your subscription has expired                 │
│                                                     │
│   Renew your plan to continue using ManaHRMS.       │
│                                                     │
│   [View Plans & Renew]                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

"View Plans & Renew" takes them to the subscription page.

---

### Seat Limit Warning

When adding an employee and the server returns `"Seat limit reached"`, show:

```
⚠️ You've used all your seats (10/10).

To add more employees, either:
• Increase your seat count  →  [Add Seats]
• Upgrade your plan         →  [Upgrade Plan]
```

---

## 9. Error Reference

| HTTP | `error_code` / `detail` | Cause | What to show |
|---|---|---|---|
| `400` | `SUBSCRIPTION_EXISTS` | Called POST /create but subscription already exists | Call PATCH /upgrade instead |
| `400` | `"Invalid add-on type"` | Wrong addon_type value | Should not happen if using enum values |
| `400` | `"Invalid payment signature"` | Razorpay verification failed | "Payment verification failed. Try again." |
| `403` | `SUBSCRIPTION_EXPIRED` | Period ended | Show renewal screen |
| `403` | `"Only admins can …"` | Non-admin tried subscription action | Hide buttons from non-admins |
| `404` | `PLAN_NOT_FOUND` | plan_id UUID doesn't match any plan | Re-fetch plans list |
| `404` | `SUBSCRIPTION_NOT_FOUND` | Called upgrade/update-seats with no subscription | Call POST /create first |
| `500` | `"Failed to create/upgrade subscription: …"` | Server error | "Something went wrong. Please try again." |

---

## 10. Flow Diagrams

### New Company — First Subscription

```
Company registers
      │
      ▼
GET /subscriptions/plans     ← show plan picker
      │
Admin picks plan + seats + billing
      │
      ▼
POST /subscriptions/create
      │
      ├── 201 Created ──────→ Show success + subscription details
      │
      └── 400 SUBSCRIPTION_EXISTS ──→ use PATCH /upgrade instead
```

### Existing Company — Renewal / Plan Change

```
Admin opens subscription page
      │
GET /subscriptions/current    ← check status
      │
      ├── status: active ──→ Show current plan, "Change Plan" option
      │
      └── status: expired/cancelled ──→ Show "Renew Now" banner
                │
                ▼
           GET /subscriptions/plans   ← show options
                │
           Admin picks new plan / billing / seats
                │
                ▼
           PATCH /subscriptions/upgrade
                │
                └── 200 OK ──→ Access restored, show new plan
```

### AI Add-on Purchase

```
AI queries run out (ai_remaining = 0)
      │
      ▼
Show "Buy AI Credits" modal
      │
Admin picks pack (1000 or 5000)
      │
      ▼
POST /subscriptions/ai-addon/order
      │
      ▼
Open Razorpay payment popup (use order_id + key)
      │
User completes payment
      │
Razorpay returns: payment_id, order_id, signature
      │
      ▼
POST /subscriptions/ai-addon/verify?payment_id=...&order_id=...&signature=...&addon_type=AI_1000_PACK
      │
      └── 200 OK ──→ Queries added, refresh GET /subscriptions/current
```

---

## Quick Reference — All Subscription Endpoints

```
GET    /subscriptions/plans                    Public — list all plans
POST   /subscriptions/create                   Admin — first-time subscription (no existing sub)
PATCH  /subscriptions/upgrade                  Admin — change plan / renew / switch billing ← NEW
PATCH  /subscriptions/update-seats             Admin — change seat count only
POST   /subscriptions/cancel                   Admin — cancel subscription
GET    /subscriptions/current                  Any user — dashboard info
POST   /subscriptions/ai-addon/order           Admin — create Razorpay order for AI pack
POST   /subscriptions/ai-addon/verify          Admin — verify payment + apply AI credits
```
