# Subscription & AI Credits API Documentation

Complete API documentation for subscription management and AI credits system in ManaHRMS Backend.

---

## Table of Contents

1. [Overview](#overview)
2. [Subscription Management APIs](#subscription-management-apis)
3. [AI Credits & Usage APIs](#ai-credits--usage-apis)
4. [Webhook APIs](#webhook-apis)
5. [Subscription Expiration & Access Control](#subscription-expiration--access-control)
6. [Error Codes](#error-codes)
7. [Examples](#examples)

---

## Overview

### Subscription System

The subscription system manages:
- **Subscription Plans**: Starter, Growth, Scale (with monthly/yearly billing)
- **Per-seat billing**: Companies pay based on number of employees
- **Trial periods**: New subscriptions start with trial status
- **Billing cycles**: Monthly or Yearly
- **Status tracking**: Trial, Active, Past Due, Cancelled, Expired

### AI Credits System

The AI credits system manages:
- **Monthly AI query limits**: Based on subscription plan
- **Usage tracking**: Per-query token tracking
- **Add-on purchases**: Additional AI queries can be purchased
- **Monthly reset**: Limits reset at the start of each month

### Subscription Expiration

**Important**: If a subscription expires, users will be automatically logged out and cannot access the system until the subscription is renewed.

---

## Subscription Management APIs

### 1. Get All Subscription Plans

Get a list of all available subscription plans.

**Endpoint:** `GET /api/v1/subscriptions/plans`

**Authentication:** Not required

**Request:**
```http
GET /api/v1/subscriptions/plans
```

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Starter",
    "plan_key": "starter",
    "price_per_user_monthly": 299.00,
    "price_per_user_yearly": 239.20,
    "minimum_seats": 1,
    "ai_queries_limit": 100,
    "features": {
      "basic_features": true,
      "advanced_reporting": false
    },
    "is_active": true
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Growth",
    "plan_key": "growth",
    "price_per_user_monthly": 599.00,
    "price_per_user_yearly": 479.20,
    "minimum_seats": 5,
    "ai_queries_limit": 500,
    "features": {
      "basic_features": true,
      "advanced_reporting": true
    },
    "is_active": true
  }
]
```

**Response Fields:**
- `id` (string, UUID): Plan unique identifier
- `name` (string): Plan display name
- `plan_key` (string): Plan key identifier
- `price_per_user_monthly` (decimal): Monthly price per user in INR
- `price_per_user_yearly` (decimal): Yearly price per user in INR (20% discount)
- `minimum_seats` (integer): Minimum number of seats required
- `ai_queries_limit` (integer): Monthly AI query limit included in plan
- `features` (object): Plan feature flags
- `is_active` (boolean): Whether plan is currently available

---

### 2. Create Subscription

Create a new subscription for the company.

**Endpoint:** `POST /api/v1/subscriptions/create`

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "billing_cycle": "monthly",
  "seat_count": 5
}
```

**Request Fields:**
- `plan_id` (string, UUID, required): Subscription plan ID
- `billing_cycle` (enum, required): `"monthly"` or `"yearly"`
- `seat_count` (integer, required, min: 1): Number of seats requested

**Response:** `201 Created`
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "company_id": 1,
  "plan": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Starter",
    "plan_key": "starter",
    "price_per_user_monthly": 299.00,
    "price_per_user_yearly": 239.20,
    "minimum_seats": 1,
    "ai_queries_limit": 100,
    "features": {},
    "is_active": true
  },
  "billing_cycle": "monthly",
  "seat_count": 5,
  "billable_seats": 5,
  "price_per_user": 299.00,
  "monthly_cost": 1495.00,
  "status": "trial",
  "current_period_start": "2024-01-01T00:00:00Z",
  "current_period_end": "2024-01-31T23:59:59Z",
  "trial_end": "2024-01-15T23:59:59Z",
  "cancel_at_period_end": false,
  "razorpay_subscription_id": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Response Fields:**
- `id` (string, UUID): Subscription ID
- `company_id` (integer): Company ID
- `plan` (object): Subscription plan details
- `billing_cycle` (string): `"monthly"` or `"yearly"`
- `seat_count` (integer): Requested seat count
- `billable_seats` (integer): Actual billable seats (max of seat_count and minimum_seats)
- `price_per_user` (decimal): Price per user based on billing cycle
- `monthly_cost` (decimal): Total monthly cost (billable_seats × price_per_user)
- `status` (string): `"trial"`, `"active"`, `"past_due"`, `"cancelled"`, or `"expired"`
- `current_period_start` (datetime): Current billing period start
- `current_period_end` (datetime): Current billing period end
- `trial_end` (datetime): Trial period end date
- `cancel_at_period_end` (boolean): Whether subscription will cancel at period end
- `razorpay_subscription_id` (string, nullable): Razorpay subscription ID
- `created_at` (datetime): Subscription creation timestamp
- `updated_at` (datetime): Last update timestamp

**Error Responses:**
- `400 Bad Request`: Invalid plan_id, billing_cycle, or seat_count
- `403 Forbidden`: User is not an admin
- `404 Not Found`: Plan not found
- `409 Conflict`: Company already has an active subscription
- `500 Internal Server Error`: Server error

---

### 3. Update Subscription Seats

Update the number of seats in an existing subscription.

**Endpoint:** `PATCH /api/v1/subscriptions/update-seats`

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "seat_count": 12
}
```

**Request Fields:**
- `seat_count` (integer, required, min: 1): New number of seats

**Response:** `200 OK`
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "company_id": 1,
  "plan": { ... },
  "billing_cycle": "monthly",
  "seat_count": 12,
  "billable_seats": 12,
  "price_per_user": 299.00,
  "monthly_cost": 3588.00,
  "status": "active",
  "current_period_start": "2024-01-01T00:00:00Z",
  "current_period_end": "2024-01-31T23:59:59Z",
  "trial_end": null,
  "cancel_at_period_end": false,
  "razorpay_subscription_id": "sub_xxx",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid seat_count or no active subscription
- `403 Forbidden`: User is not an admin
- `404 Not Found`: No active subscription found
- `500 Internal Server Error`: Server error

---

### 4. Cancel Subscription

Cancel an active subscription.

**Endpoint:** `POST /api/v1/subscriptions/cancel`

**Authentication:** Required (Admin only)

**Query Parameters:**
- `cancel_at_period_end` (boolean, default: `true`): Whether to cancel at period end or immediately

**Request:**
```http
POST /api/v1/subscriptions/cancel?cancel_at_period_end=true
```

**Response:** `200 OK`
```json
{
  "message": "Subscription will be cancelled at period end",
  "success": true
}
```

**Response Fields:**
- `message` (string): Success message
- `success` (boolean): Always `true` on success

**Error Responses:**
- `403 Forbidden`: User is not an admin
- `404 Not Found`: No active subscription found
- `500 Internal Server Error`: Server error

---

### 5. Get Current Subscription

Get current subscription information for dashboard display.

**Endpoint:** `GET /api/v1/subscriptions/current`

**Authentication:** Required

**Request:**
```http
GET /api/v1/subscriptions/current
```

**Response:** `200 OK`
```json
{
  "plan": "Starter",
  "plan_key": "starter",
  "employees_used": 8,
  "billable_seats": 10,
  "price_per_user": 299.00,
  "monthly_cost": 2990.00,
  "billing_cycle": "monthly",
  "ai_usage": 45,
  "ai_limit": 100,
  "ai_remaining": 55,
  "next_billing_date": "2024-02-01T00:00:00Z",
  "status": "active",
  "is_trial": false,
  "trial_end": null
}
```

**Response Fields:**
- `plan` (string): Plan name
- `plan_key` (string): Plan key identifier
- `employees_used` (integer): Current number of active employees
- `billable_seats` (integer): Number of billable seats
- `price_per_user` (decimal): Price per user
- `monthly_cost` (decimal): Total monthly cost
- `billing_cycle` (string): `"monthly"` or `"yearly"`
- `ai_usage` (integer): AI queries used this month
- `ai_limit` (integer): Total AI query limit (plan + add-ons)
- `ai_remaining` (integer): Remaining AI queries this month
- `next_billing_date` (datetime, nullable): Next billing date
- `status` (string): Subscription status
- `is_trial` (boolean): Whether subscription is in trial
- `trial_end` (datetime, nullable): Trial end date

**Error Responses:**
- `404 Not Found`: No subscription found
- `500 Internal Server Error`: Server error

---

### 6. Create AI Add-on Order

Create a Razorpay order for purchasing AI add-on credits.

**Endpoint:** `POST /api/v1/subscriptions/ai-addon/order`

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "addon_type": "AI_1000_PACK"
}
```

**Request Fields:**
- `addon_type` (enum, required): `"AI_1000_PACK"` or `"AI_5000_PACK"`

**Add-on Types:**
- `AI_1000_PACK`: +1000 AI queries for ₹199
- `AI_5000_PACK`: +5000 AI queries for ₹799

**Response:** `200 OK`
```json
{
  "order_id": "order_xxx",
  "amount": 199.00,
  "currency": "INR",
  "key": "rzp_test_xxx"
}
```

**Response Fields:**
- `order_id` (string): Razorpay order ID
- `amount` (decimal): Order amount in INR
- `currency` (string): Currency code (always "INR")
- `key` (string): Razorpay key ID for frontend integration

**Error Responses:**
- `400 Bad Request`: Invalid addon_type
- `403 Forbidden`: User is not an admin
- `500 Internal Server Error`: Server error

---

### 7. Verify AI Add-on Payment

Verify and apply AI add-on purchase after payment.

**Endpoint:** `POST /api/v1/subscriptions/ai-addon/verify`

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "payment_id": "pay_xxx",
  "order_id": "order_xxx",
  "signature": "signature_xxx",
  "addon_type": "AI_1000_PACK"
}
```

**Request Fields:**
- `payment_id` (string, required): Razorpay payment ID
- `order_id` (string, required): Razorpay order ID
- `signature` (string, required): Payment signature for verification
- `addon_type` (enum, required): `"AI_1000_PACK"` or `"AI_5000_PACK"`

**Response:** `200 OK`
```json
{
  "message": "AI add-on purchased successfully. 1000 queries added.",
  "success": true
}
```

**Response Fields:**
- `message` (string): Success message with queries added
- `success` (boolean): Always `true` on success

**Error Responses:**
- `400 Bad Request`: Invalid payment signature or addon_type
- `403 Forbidden`: User is not an admin
- `500 Internal Server Error`: Server error

---

## AI Credits & Usage APIs

### 1. Ask AI Chatbot

Ask the AI chatbot a question about company data.

**Endpoint:** `POST /api/v1/ai-chat/ask`

**Authentication:** Required

**Request Body:**
```json
{
  "question": "How many employees do we have?",
  "conversation_history": [
    {
      "role": "user",
      "content": "What departments do we have?"
    },
    {
      "role": "assistant",
      "content": "You have 5 departments: Engineering, Sales, Marketing, HR, and Finance."
    }
  ]
}
```

**Request Fields:**
- `question` (string, required, min_length: 1): User's question in natural language
- `conversation_history` (array, optional): Previous conversation messages for context

**Conversation History Fields:**
- `role` (string, required): `"user"` or `"assistant"`
- `content` (string, required): Message content

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Based on the company data, you have 25 active employees across 5 departments.",
  "question": "How many employees do we have?"
}
```

**Response Fields:**
- `success` (boolean): Whether the query was successful
- `message` (string): AI assistant's response
- `question` (string): The question that was asked

**Error Responses:**
- `400 Bad Request`: Invalid question or missing AI credits
- `401 Unauthorized`: Invalid or expired token
- `403 Forbidden`: Subscription expired or inactive
- `429 Too Many Requests`: AI usage limit reached
- `500 Internal Server Error`: Server error or AI service unavailable

**AI Usage Limit Check:**
- The system automatically checks if the company has remaining AI queries
- If limit is reached, returns `success: false` with error message
- Each query consumes tokens (estimated based on question and response length)

---

## Webhook APIs

### 1. Razorpay Webhook

Handle Razorpay webhook events for subscription and payment updates.

**Endpoint:** `POST /api/v1/webhooks/razorpay`

**Authentication:** Not required (uses signature verification)

**Headers:**
- `X-Razorpay-Signature` (string, required): Webhook signature for verification

**Request Body:**
```json
{
  "event": "subscription.activated",
  "payload": {
    "subscription": {
      "id": "sub_xxx",
      "status": "active",
      "current_start": 1704067200,
      "current_end": 1706745599
    }
  }
}
```

**Supported Events:**
- `subscription.activated`: Subscription activated
- `subscription.charged`: Subscription charged (renewal)
- `invoice.paid`: Invoice paid successfully
- `invoice.failed`: Invoice payment failed
- `subscription.cancelled`: Subscription cancelled
- `payment.captured`: Payment captured (for one-time payments like AI add-ons)

**Response:** `200 OK`
```json
{
  "status": "success"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid webhook signature
- `500 Internal Server Error`: Server error processing webhook

---

## Subscription Expiration & Access Control

### Automatic Logout on Expiration

**Important Security Feature**: If a subscription expires, all users from that company are automatically logged out and cannot access the system until the subscription is renewed.

### How It Works

1. **Authentication Check**: Every API request (except public endpoints) checks subscription status
2. **Expiration Detection**: System checks if:
   - Subscription status is `"expired"` or `"cancelled"`
   - `current_period_end` date has passed
   - Trial period has ended without activation
3. **Automatic Logout**: If subscription is expired:
   - Returns `403 Forbidden` with error code `SUBSCRIPTION_EXPIRED`
   - Frontend should immediately log out the user
   - User cannot access any protected endpoints

### Subscription Status Flow

```
Trial → Active → Past Due → Expired
  ↓        ↓         ↓
Cancelled (at any point)
```

### Status Definitions

- **Trial**: New subscription in trial period (typically 14 days)
- **Active**: Subscription is active and paid
- **Past Due**: Payment failed but grace period active
- **Cancelled**: Subscription cancelled (access until period end)
- **Expired**: Subscription expired, no access allowed

### API Response on Expiration

When a user with an expired subscription tries to access any protected endpoint:

**Response:** `403 Forbidden`
```json
{
  "success": false,
  "message": "Your subscription has expired. Please renew to continue using the service.",
  "error_code": "SUBSCRIPTION_EXPIRED"
}
```

### Excluded Endpoints

The following endpoints are accessible even with expired subscription:
- `POST /api/v1/auth/register` - Company registration
- `POST /api/v1/auth/login` - Login (will fail if subscription expired)
- `GET /api/v1/subscriptions/plans` - View plans
- `POST /api/v1/subscriptions/create` - Create new subscription
- `POST /api/v1/webhooks/razorpay` - Webhook handler

---

## Error Codes

### Authentication Errors
- `INVALID_TOKEN`: Invalid or malformed JWT token
- `INVALID_TOKEN_PAYLOAD`: Token payload is invalid
- `USER_NOT_FOUND`: User does not exist
- `USER_INACTIVE`: User account is inactive
- `COMPANY_INACTIVE`: Company account is inactive
- `SUBSCRIPTION_EXPIRED`: Subscription has expired

### Authorization Errors
- `ADMIN_ACCESS_REQUIRED`: Admin role required
- `EMPLOYEE_ACCESS_REQUIRED`: Employee role required
- `SUPERUSER_ACCESS_REQUIRED`: Superuser privileges required

### Subscription Errors
- `SUBSCRIPTION_NOT_FOUND`: No active subscription found
- `SUBSCRIPTION_ALREADY_EXISTS`: Company already has active subscription
- `INVALID_PLAN`: Plan ID is invalid or plan is inactive
- `INVALID_SEAT_COUNT`: Seat count is below minimum requirement
- `PAYMENT_FAILED`: Payment processing failed

### AI Credits Errors
- `AI_LIMIT_REACHED`: Monthly AI query limit reached
- `AI_SERVICE_UNAVAILABLE`: AI service is not configured
- `INSUFFICIENT_CREDITS`: Not enough AI credits remaining

---

## Examples

### Complete Subscription Flow

#### 1. Get Available Plans
```bash
curl -X GET "https://api.manahrms.com/api/v1/subscriptions/plans"
```

#### 2. Create Subscription
```bash
curl -X POST "https://api.manahrms.com/api/v1/subscriptions/create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "550e8400-e29b-41d4-a716-446655440000",
    "billing_cycle": "monthly",
    "seat_count": 5
  }'
```

#### 3. Check Current Subscription
```bash
curl -X GET "https://api.manahrms.com/api/v1/subscriptions/current" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 4. Update Seats
```bash
curl -X PATCH "https://api.manahrms.com/api/v1/subscriptions/update-seats" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seat_count": 10
  }'
```

### AI Credits Flow

#### 1. Check AI Usage (via Current Subscription)
```bash
curl -X GET "https://api.manahrms.com/api/v1/subscriptions/current" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response includes:
```json
{
  "ai_usage": 45,
  "ai_limit": 100,
  "ai_remaining": 55
}
```

#### 2. Purchase AI Add-on
```bash
# Step 1: Create order
curl -X POST "https://api.manahrms.com/api/v1/subscriptions/ai-addon/order" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "addon_type": "AI_1000_PACK"
  }'

# Step 2: After payment, verify
curl -X POST "https://api.manahrms.com/api/v1/subscriptions/ai-addon/verify" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay_xxx",
    "order_id": "order_xxx",
    "signature": "signature_xxx",
    "addon_type": "AI_1000_PACK"
  }'
```

#### 3. Use AI Chat
```bash
curl -X POST "https://api.manahrms.com/api/v1/ai-chat/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many employees are in the Engineering department?",
    "conversation_history": null
  }'
```

### Handling Subscription Expiration

#### Frontend Implementation

```javascript
// Example: Handle subscription expiration
async function makeApiCall(url, options) {
  try {
    const response = await fetch(url, options);
    
    if (response.status === 403) {
      const error = await response.json();
      
      if (error.error_code === 'SUBSCRIPTION_EXPIRED') {
        // Logout user immediately
        localStorage.removeItem('token');
        window.location.href = '/subscription-expired';
        return;
      }
    }
    
    return response;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

---

## Notes

1. **Trial Period**: New subscriptions start with a 14-day trial period
2. **Seat Calculation**: Billable seats = max(requested_seats, minimum_seats)
3. **AI Limits**: Reset monthly at the start of each month
4. **Add-ons**: AI add-ons are applied to the current month
5. **Webhooks**: Must be configured in Razorpay dashboard
6. **Currency**: All prices are in INR (Indian Rupees)
7. **Timezone**: All dates are in UTC

---

## Support

For issues or questions:
- Check error codes in responses
- Review subscription status via `/api/v1/subscriptions/current`
- Verify Razorpay webhook configuration
- Check server logs for detailed error messages




