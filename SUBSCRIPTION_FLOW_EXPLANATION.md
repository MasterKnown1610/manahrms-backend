# Subscription Flow Explanation

This document explains the complete subscription flow in the ManaHRMS backend system.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Subscription Creation Flow](#subscription-creation-flow)
3. [Subscription Status Lifecycle](#subscription-status-lifecycle)
4. [Seat Management](#seat-management)
5. [AI Usage Tracking](#ai-usage-tracking)
6. [Payment Processing](#payment-processing)
7. [Webhook Handling](#webhook-handling)
8. [Access Control](#access-control)
9. [Key Components](#key-components)

---

## Overview

The subscription system manages:
- **Subscription Plans**: Different tiers (Starter, Growth, Scale) with varying features
- **Company Subscriptions**: Active subscriptions for each company
- **Seat Management**: Employee count limits and billing
- **AI Credits**: Monthly AI query limits and add-on purchases
- **Payment Integration**: Razorpay for recurring and one-time payments

---

## Subscription Creation Flow

### Step-by-Step Process

```
1. User (Admin) → GET /api/v1/subscriptions/plans
   ↓
2. Frontend displays available plans
   ↓
3. User selects plan → POST /api/v1/subscriptions/create
   {
     "plan_id": "uuid",
     "billing_cycle": "monthly" | "yearly",
     "seat_count": 10
   }
   ↓
4. Backend Processing:
   a. Verify user is admin
   b. Check if company already has active subscription
   c. Get subscription plan details
   d. Create Razorpay customer (if configured)
   e. Calculate billable seats (max(seat_count, minimum_seats))
   f. Calculate price per user based on billing cycle
   g. Calculate billing period (30 days for monthly, 365 for yearly)
   ↓
5. Create Database Records:
   - CompanySubscription (status: ACTIVE)
   - SubscriptionUsage (employees_used: 0, billable_seats: calculated)
   - CompanyAIUsage (queries_used: 0, queries_limit: from plan)
   ↓
6. Return subscription details to frontend
```

### Key Calculations

**Billable Seats:**
```python
billable_seats = max(seat_count, plan.minimum_seats)
# Example: If user requests 5 seats but plan minimum is 10, billable_seats = 10
```

**Price Per User:**
```python
if billing_cycle == MONTHLY:
    price_per_user = plan.price_per_user_monthly
else:
    price_per_user = plan.price_per_user_yearly
```

**Monthly Cost:**
```python
monthly_cost = billable_seats * price_per_user
```

**Billing Period:**
```python
if billing_cycle == MONTHLY:
    period_end = now + 30 days
else:
    period_end = now + 365 days
```

---

## Subscription Status Lifecycle

### Status States

```
ACTIVE → PAST_DUE → EXPIRED
   ↓
CANCELLED
```

### Status Transitions

1. **ACTIVE**
   - Initial status when subscription is created
   - Company has full access to features
   - Billing is current

2. **PAST_DUE**
   - Payment failed for recurring subscription
   - Set via Razorpay webhook (`invoice.failed`)
   - Access may be restricted (depends on configuration)

3. **EXPIRED**
   - Subscription period has ended
   - Set automatically when `current_period_end < now`
   - Users are logged out and cannot access the system

4. **CANCELLED**
   - Subscription cancelled by admin
   - If `cancel_at_period_end = true`: Access until period end
   - If `cancel_at_period_end = false`: Immediate cancellation

### Status Checks

**On Every API Request:**
```python
# In get_current_authenticated_user dependency:
1. Check if subscription exists
2. Check if subscription is EXPIRED or CANCELLED
3. Check if current_period_end < now
4. If expired → Return 403 Forbidden, user logged out
```

---

## Seat Management

### Seat Calculation

**When Creating Subscription:**
```python
seat_count = user_requested_seats  # e.g., 5
minimum_seats = plan.minimum_seats   # e.g., 10
billable_seats = max(5, 10) = 10    # User pays for 10 seats
```

**When Updating Seats:**
```python
# PATCH /api/v1/subscriptions/update-seats
{
  "seat_count": 15
}

# Backend:
1. Get current subscription
2. Calculate new_billable_seats = max(15, plan.minimum_seats)
3. Update subscription.billable_seats
4. Update SubscriptionUsage.billable_seats
5. Update Razorpay subscription quantity (if integrated)
```

### Seat Availability Check

**Before Adding Employee:**
```python
# Check if company can add more employees
usage = SubscriptionUsage.query.filter(company_id=company_id).first()

if usage.employees_used >= usage.billable_seats:
    return False, "Seat limit reached"
else:
    return True, None
```

**Employee Count Sync:**
```python
# Sync actual employee count with subscription
active_employees = count(Employee where status='active')
usage.employees_used = active_employees
```

---

## AI Usage Tracking

### Monthly AI Limits

**Initial Setup:**
```python
# When subscription is created:
ai_usage = CompanyAIUsage(
    company_id=company_id,
    year=2024,
    month=3,
    queries_used=0,
    queries_limit=plan.ai_queries_limit,  # e.g., 1000
    extra_queries_purchased=0
)
```

**Total Limit Calculation:**
```python
total_limit = queries_limit + extra_queries_purchased
# Example: 1000 (base) + 5000 (add-on) = 6000 total
```

**Recording AI Usage:**
```python
# When user makes AI query:
1. Get current month's CompanyAIUsage
2. Check if queries_used < total_limit
3. If limit reached → Return error
4. If OK → Increment queries_used += 1
5. Create AIUsage record (for audit)
```

### AI Add-on Purchase Flow

```
1. User → POST /api/v1/subscriptions/ai-addon/order
   {
     "addon_type": "AI_1000_PACK" | "AI_5000_PACK"
   }
   ↓
2. Backend creates Razorpay order
   - AI_1000_PACK: ₹199
   - AI_5000_PACK: ₹799
   ↓
3. Frontend processes payment via Razorpay
   ↓
4. User → POST /api/v1/subscriptions/ai-addon/verify
   {
     "payment_id": "...",
     "order_id": "...",
     "signature": "...",
     "addon_type": "AI_1000_PACK"
   }
   ↓
5. Backend:
   a. Verify payment signature
   b. Get current month's CompanyAIUsage
   c. Add queries: extra_queries_purchased += 1000 (or 5000)
   d. Create AIAddon record
   ↓
6. Queries immediately available for use
```

**Important:** Add-ons apply to the current month only. They reset at the start of the next month.

---

## Payment Processing

### Razorpay Integration

**Customer Creation:**
```python
# When creating subscription:
customer = razorpay_service.create_customer(
    name=company.company_name,
    email=company.email,
    contact=company.phone
)
razorpay_customer_id = customer["id"]
```

**Subscription Creation (Future):**
```python
# In production, you would:
1. Create Razorpay plan
2. Create Razorpay subscription
3. Link razorpay_subscription_id to CompanySubscription
```

**Payment Verification:**
```python
# For AI add-ons:
is_valid = razorpay_service.verify_payment_signature(
    payment_id=payment_id,
    order_id=order_id,
    signature=signature
)
```

---

## Webhook Handling

### Razorpay Webhooks

**Endpoint:** `POST /api/v1/webhooks/razorpay`

**Signature Verification:**
```python
1. Get raw request body
2. Get X-Razorpay-Signature header
3. Verify HMAC signature
4. If invalid → Return 401 Unauthorized
```

**Handled Events:**

1. **subscription.activated**
   ```python
   - Set subscription.status = ACTIVE
   - Set current_period_start = now
   - Calculate current_period_end
   ```

2. **subscription.charged**
   ```python
   - Update current_period_start = now
   - Extend current_period_end by billing cycle
   ```

3. **invoice.paid**
   ```python
   - Set subscription.status = ACTIVE
   - Payment successful
   ```

4. **invoice.failed**
   ```python
   - Set subscription.status = PAST_DUE
   - Payment failed
   ```

5. **subscription.cancelled**
   ```python
   - Set subscription.status = CANCELLED
   - Set cancelled_at = now
   ```

6. **payment.captured**
   ```python
   - Log one-time payment (for AI add-ons)
   - Actual processing done via verify endpoint
   ```

---

## Access Control

### Authentication Dependency

**Every Protected Endpoint:**
```python
@router.get("/some-endpoint")
async def some_endpoint(
    current_user: User = Depends(get_current_authenticated_user),
    ...
):
    # User is authenticated and subscription is valid
```

**Subscription Check Flow:**
```python
def get_current_authenticated_user(...):
    1. Verify JWT token
    2. Get user from database
    3. Get company subscription
    4. Check subscription status:
       - If no subscription → 403 Forbidden
       - If EXPIRED → 403 Forbidden (user logged out)
       - If CANCELLED → 403 Forbidden (user logged out)
       - If current_period_end < now → 403 Forbidden
    5. Return user (if all checks pass)
```

**Special Endpoint (Allow Expired):**
```python
# For subscription creation/renewal:
@router.post("/create")
async def create_subscription(
    current_user: User = Depends(get_current_authenticated_user_allow_expired),
    ...
):
    # Allows users with expired subscriptions to create new ones
```

---

## Key Components

### Database Models

1. **SubscriptionPlan**
   - Plan definitions (Starter, Growth, Scale)
   - Pricing, features, limits

2. **CompanySubscription**
   - Active subscription for each company
   - Status, billing cycle, periods
   - Links to Razorpay

3. **SubscriptionUsage**
   - Employee count tracking
   - Billable seats vs. used seats

4. **CompanyAIUsage**
   - Monthly AI query tracking
   - Base limit + add-ons

5. **AIUsage**
   - Individual query records (audit trail)

6. **AIAddon**
   - Add-on purchase records

### Service Layer

**SubscriptionService:**
- `create_subscription()` - Create new subscription
- `update_subscription_seats()` - Update seat count
- `cancel_subscription()` - Cancel subscription
- `get_company_subscription()` - Get active subscription
- `check_seat_availability()` - Check if can add employees
- `check_ai_usage_limit()` - Check if can make AI queries
- `record_ai_usage()` - Record AI query
- `purchase_ai_addon()` - Purchase AI add-on
- `get_current_subscription_info()` - Get dashboard info

### API Endpoints

**Subscription Management:**
- `GET /api/v1/subscriptions/plans` - List all plans
- `POST /api/v1/subscriptions/create` - Create subscription
- `PATCH /api/v1/subscriptions/update-seats` - Update seats
- `POST /api/v1/subscriptions/cancel` - Cancel subscription
- `GET /api/v1/subscriptions/current` - Get current subscription

**AI Add-ons:**
- `POST /api/v1/subscriptions/ai-addon/order` - Create payment order
- `POST /api/v1/subscriptions/ai-addon/verify` - Verify and apply payment

**Webhooks:**
- `POST /api/v1/webhooks/razorpay` - Razorpay webhook handler

---

## Example Flows

### Complete Subscription Lifecycle

```
Day 1: Company signs up
  → Admin creates subscription (ACTIVE)
  → 10 seats, ₹500/month
  → 1000 AI queries/month

Day 15: Company grows
  → Admin updates to 20 seats
  → Billable seats: 20
  → Monthly cost: ₹1000

Day 20: AI limit reached
  → Admin purchases AI_5000_PACK
  → Total AI limit: 6000 queries
  → Queries available immediately

Day 30: Billing period ends
  → Razorpay charges subscription
  → Webhook: subscription.charged
  → Period extended by 30 days

Day 45: Payment fails
  → Razorpay webhook: invoice.failed
  → Status: PAST_DUE
  → Access may be restricted

Day 50: Payment retry succeeds
  → Razorpay webhook: invoice.paid
  → Status: ACTIVE
  → Full access restored

Day 60: Company cancels
  → Admin cancels subscription
  → cancel_at_period_end = true
  → Access until period end

Day 90: Period ends
  → Status: CANCELLED
  → Users logged out
  → No access until renewal
```

---

## Important Notes

1. **No Trial Period**: Subscriptions start as ACTIVE immediately (trial removed)

2. **Minimum Seats**: Users always pay for at least `plan.minimum_seats`, even if they request fewer

3. **AI Limits Reset**: Monthly AI limits reset at the start of each month

4. **Add-ons are Monthly**: AI add-ons apply only to the current month

5. **Expired Subscriptions**: Users with expired subscriptions are automatically logged out

6. **Webhook Security**: All Razorpay webhooks are verified using HMAC signatures

7. **Seat Sync**: Employee count is synced with subscription usage, but billing is based on `billable_seats`

---

## Error Handling

**Common Errors:**

- `NO_ACTIVE_SUBSCRIPTION` - Company has no subscription
- `SUBSCRIPTION_EXPIRED` - Subscription expired, user logged out
- `SUBSCRIPTION_EXISTS` - Company already has active subscription
- `PLAN_NOT_FOUND` - Invalid plan ID
- `SEAT_LIMIT_REACHED` - Cannot add more employees
- `AI_USAGE_LIMIT_REACHED` - AI query limit exceeded

---

This completes the subscription flow explanation. For API documentation, see `SUBSCRIPTION_AND_AI_CREDITS_API_DOCUMENTATION.md`.




