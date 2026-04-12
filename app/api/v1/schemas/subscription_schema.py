"""
Subscription and Billing Schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.api.v1.models.subscription_model import BillingCycle, SubscriptionStatus, AIAddonType


# Request Schemas
class SubscriptionCreateRequest(BaseModel):
    """Schema for creating a subscription"""
    plan_id: str = Field(..., description="Subscription plan ID (UUID)")
    billing_cycle: BillingCycle = Field(..., description="Monthly or yearly billing")
    seat_count: int = Field(..., ge=1, description="Number of seats requested")


class SubscriptionUpdateSeatsRequest(BaseModel):
    """Schema for updating subscription seats"""
    seat_count: int = Field(..., ge=1, description="New number of seats")


class SubscriptionUpgradeRequest(BaseModel):
    """Schema for upgrading / changing the current subscription plan"""
    plan_id: str = Field(..., description="New subscription plan ID (UUID)")
    billing_cycle: BillingCycle = Field(..., description="Monthly or yearly billing")
    seat_count: int = Field(..., ge=1, description="Number of seats requested")


class AIAddonPurchaseRequest(BaseModel):
    """Schema for purchasing AI add-on"""
    addon_type: AIAddonType = Field(..., description="Type of AI add-on to purchase")


# Response Schemas
class SubscriptionPlanResponse(BaseModel):
    """Schema for subscription plan response"""
    id: str
    name: str
    plan_key: str
    price_per_user_monthly: Decimal
    price_per_user_yearly: Decimal
    minimum_seats: int
    ai_queries_limit: int
    features: Optional[Dict[str, Any]] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Schema for subscription response"""
    id: str
    company_id: int
    plan: SubscriptionPlanResponse
    billing_cycle: BillingCycle
    seat_count: int
    billable_seats: int
    price_per_user: Decimal
    monthly_cost: Decimal  # Calculated: billable_seats * price_per_user
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    razorpay_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionUsageResponse(BaseModel):
    """Schema for subscription usage response"""
    company_id: int
    employees_used: int
    billable_seats: int
    last_synced_at: datetime
    
    class Config:
        from_attributes = True


class AIUsageResponse(BaseModel):
    """Schema for AI usage response"""
    company_id: int
    queries_used: int
    queries_limit: int
    extra_queries_purchased: int
    total_limit: int
    remaining_queries: int
    month: int
    year: int
    
    class Config:
        from_attributes = True


class CurrentSubscriptionResponse(BaseModel):
    """Schema for current subscription dashboard"""
    plan: Optional[str] = None
    plan_key: Optional[str] = None
    employees_used: int
    billable_seats: int
    price_per_user: Decimal
    monthly_cost: Decimal
    billing_cycle: Optional[BillingCycle] = None
    ai_usage: int
    ai_limit: int
    ai_remaining: int
    next_billing_date: Optional[datetime] = None
    status: Optional[SubscriptionStatus] = None


class RazorpayOrderResponse(BaseModel):
    """Schema for Razorpay order creation response"""
    order_id: str
    amount: Decimal
    currency: str
    key: str  # Razorpay key ID


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True

