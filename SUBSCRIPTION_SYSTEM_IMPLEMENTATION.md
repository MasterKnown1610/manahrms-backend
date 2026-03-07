# Subscription System Implementation Summary

## ✅ Implementation Complete

A comprehensive subscription and billing system has been implemented for the ManaHRMS multi-tenant SaaS platform with Razorpay integration.

---

## 📁 Files Created

### Database Models
- **`app/api/v1/models/subscription_model.py`**
  - `SubscriptionPlan`: Subscription plan definitions
  - `CompanySubscription`: Company subscription records
  - `SubscriptionUsage`: Seat usage tracking
  - `AIUsage`: Individual AI query tracking
  - `CompanyAIUsage`: Monthly AI usage summary
  - `AIAddon`: AI add-on purchases

### Schemas
- **`app/api/v1/schemas/subscription_schema.py`**
  - Request/response schemas for subscription operations
  - Razorpay order response schema

### Services
- **`app/api/v1/services/razorpay_service.py`**
  - Razorpay payment gateway integration
  - Customer creation
  - Subscription management
  - Order creation
  - Payment verification
  - Webhook signature verification

- **`app/api/v1/services/subscription_service.py`**
  - Subscription creation and management
  - Seat calculation and validation
  - AI usage tracking and limits
  - Billing calculations
  - Subscription lifecycle management

### API Routes
- **`app/api/v1/routes/subscriptions.py`**
  - `GET /api/v1/subscriptions/plans` - Get all plans
  - `POST /api/v1/subscriptions/create` - Create subscription
  - `PATCH /api/v1/subscriptions/update-seats` - Update seats
  - `POST /api/v1/subscriptions/cancel` - Cancel subscription
  - `GET /api/v1/subscriptions/current` - Get current subscription info
  - `POST /api/v1/subscriptions/ai-addon/order` - Create AI add-on order
  - `POST /api/v1/subscriptions/ai-addon/verify` - Verify AI add-on payment

- **`app/api/v1/routes/webhooks.py`**
  - `POST /api/v1/webhooks/razorpay` - Razorpay webhook handler

### Initialization
- **`app/db/init_subscription_plans.py`**
  - Script to initialize default subscription plans

---

## 🔧 Files Modified

### Configuration
- **`app/core/config.py`**
  - Added Razorpay settings (KEY_ID, KEY_SECRET, WEBHOOK_SECRET)

### Dependencies
- **`requirements.txt`**
  - Added `razorpay>=1.4.0`

### Database
- **`app/db/base.py`**
  - Added subscription model imports

- **`app/api/v1/models/company_model.py`**
  - Added subscription relationship

### API Integration
- **`app/api/v1/routes/employees.py`**
  - Added seat validation before employee creation
  - Added employee count sync after creation

- **`app/api/v1/routes/ai_chat.py`**
  - Added AI usage limit check
  - Added AI usage tracking

- **`app/api/router.py`**
  - Added subscriptions and webhooks routers

---

## 📊 Subscription Plans

### Starter Plan
- **Price**: ₹49/user/month or ₹470/user/year
- **Minimum Seats**: 1
- **AI Queries**: 300/month
- **Features**: All core HRMS features

### Growth Plan
- **Price**: ₹39/user/month or ₹374.40/user/year
- **Minimum Seats**: 10
- **AI Queries**: 800/month
- **Features**: All Starter features + Advanced Analytics

### Scale Plan
- **Price**: ₹29/user/month or ₹278.40/user/year
- **Minimum Seats**: 25
- **AI Queries**: 2000/month
- **Features**: All Growth features + Custom Reports + API Access + Priority Support

---

## 💰 Billing Logic

### Seat Calculation
```
billable_seats = max(employee_count, minimum_seats)
```

**Example:**
- Growth plan (minimum_seats = 10)
- Company has 4 employees
- billable_seats = max(4, 10) = 10
- Monthly cost = 10 × ₹39 = ₹390

### Yearly Discount
- 20% discount on yearly billing
- Example: ₹49/month → ₹470/year (instead of ₹588)

---

## 🤖 AI Add-Ons

### Available Add-Ons
- **AI_1000_PACK**: +1000 queries for ₹199
- **AI_5000_PACK**: +5000 queries for ₹799

### Usage Tracking
- Monthly reset of AI query limits
- Add-ons apply to current month
- Total limit = base_limit + add_ons_purchased

---

## 🔐 Security Features

1. **Webhook Signature Verification**
   - All Razorpay webhooks are verified using HMAC signature
   - Invalid signatures are rejected

2. **Payment Verification**
   - AI add-on payments are verified before applying
   - Payment signature validation

3. **Tenant Isolation**
   - All subscription data is isolated by company_id
   - Users can only access their company's subscription

---

## 🔄 Subscription Lifecycle

1. **Trial** (14 days)
   - New subscriptions start with trial status
   - Full access during trial period

2. **Active**
   - Subscription is active and billing
   - Razorpay handles recurring payments

3. **Past Due**
   - Payment failed
   - Access may be restricted

4. **Cancelled**
   - Subscription cancelled
   - Access until period end (if cancel_at_period_end = true)

5. **Expired**
   - Subscription expired
   - No access

---

## 📡 Razorpay Webhook Events

### Handled Events
- `subscription.activated` - Subscription activated
- `subscription.charged` - Subscription charged
- `invoice.paid` - Invoice paid successfully
- `invoice.failed` - Invoice payment failed
- `subscription.cancelled` - Subscription cancelled
- `payment.captured` - One-time payment captured

---

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Razorpay
Add to `.env`:
```env
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

### 3. Run Database Migration
```bash
# Create migration
alembic revision --autogenerate -m "Add subscription tables"

# Apply migration
alembic upgrade head
```

### 4. Initialize Subscription Plans
```bash
python -m app.db.init_subscription_plans
```

### 5. Configure Razorpay Webhook
In Razorpay Dashboard:
- Webhook URL: `https://api.manahrms.com/api/v1/webhooks/razorpay`
- Events to subscribe:
  - subscription.activated
  - subscription.charged
  - invoice.paid
  - invoice.failed
  - subscription.cancelled
  - payment.captured

---

## 📝 API Usage Examples

### Get Subscription Plans
```bash
GET /api/v1/subscriptions/plans
```

### Create Subscription
```bash
POST /api/v1/subscriptions/create
{
  "plan_id": "uuid-of-starter-plan",
  "billing_cycle": "monthly",
  "seat_count": 5
}
```

### Update Seats
```bash
PATCH /api/v1/subscriptions/update-seats
{
  "seat_count": 12
}
```

### Get Current Subscription
```bash
GET /api/v1/subscriptions/current
```

### Purchase AI Add-On
```bash
# Step 1: Create order
POST /api/v1/subscriptions/ai-addon/order
{
  "addon_type": "AI_1000_PACK"
}

# Step 2: After payment, verify
POST /api/v1/subscriptions/ai-addon/verify
{
  "payment_id": "pay_xxx",
  "order_id": "order_xxx",
  "signature": "signature_xxx",
  "addon_type": "AI_1000_PACK"
}
```

---

## ✅ Features Implemented

- [x] Subscription plan management
- [x] Per-seat billing with minimum seat requirements
- [x] Monthly and yearly billing cycles
- [x] Razorpay integration
- [x] Subscription creation and management
- [x] Seat count updates
- [x] Subscription cancellation
- [x] AI usage tracking and limits
- [x] AI add-on purchases
- [x] Webhook handling
- [x] Employee seat validation
- [x] AI query limit enforcement
- [x] Subscription dashboard info

---

## 🔮 Next Steps

1. **Create Razorpay Plans**
   - Create plans in Razorpay Dashboard matching your subscription plans
   - Update subscription creation to use Razorpay plan IDs

2. **Email Notifications**
   - Send emails on subscription events
   - Trial expiration reminders
   - Payment failure notifications

3. **Usage Analytics**
   - Track subscription metrics
   - Generate usage reports
   - Monitor AI usage patterns

4. **Subscription Upgrades/Downgrades**
   - Allow plan changes
   - Prorated billing
   - Feature migration

5. **Trial Management**
   - Trial extension options
   - Trial-to-paid conversion tracking

---

## 📚 Documentation

- Razorpay API: https://razorpay.com/docs/api/
- Subscription API: See `/docs` endpoint for full API documentation

---

**Status**: ✅ Implementation Complete - Ready for Testing and Integration

