"""
SuperAdmin Schemas - Request/Response models for superadmin API
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ─── Auth ────────────────────────────────────────────────────────────────────

class SuperAdminLogin(BaseModel):
    email: EmailStr
    password: str


class SuperAdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: "SuperAdminResponse"


class SuperAdminResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Company ──────────────────────────────────────────────────────────────────

class CompanyBriefResponse(BaseModel):
    id: int
    company_code: str
    company_name: str
    email: str
    phone: Optional[str]
    company_type: str
    is_active: bool
    created_at: datetime
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_end: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyDetailResponse(BaseModel):
    id: int
    company_code: str
    company_name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    company_type: str
    gst_number: Optional[str]
    pan_number: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_users: int = 0
    total_employees: int = 0
    subscription: Optional[Any] = None

    class Config:
        from_attributes = True


class CompanyUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


# ─── Subscription ─────────────────────────────────────────────────────────────

class SubscriptionStatusEnum(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillingCycleEnum(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionDetailResponse(BaseModel):
    id: str
    company_id: int
    company_name: str
    plan_name: str
    plan_key: str
    billing_cycle: str
    seat_count: int
    billable_seats: int
    price_per_user: Decimal
    monthly_cost: Decimal
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    trial_end: Optional[datetime]
    cancel_at_period_end: bool
    cancelled_at: Optional[datetime]
    razorpay_subscription_id: Optional[str]
    razorpay_customer_id: Optional[str]
    employees_used: int = 0
    ai_queries_used: int = 0
    ai_queries_limit: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExtendSubscriptionRequest(BaseModel):
    days: Optional[int] = Field(None, ge=1, description="Number of days to extend")
    new_end_date: Optional[datetime] = Field(None, description="Set an explicit end date")

    class Config:
        json_schema_extra = {
            "example": {
                "days": 30,
                "new_end_date": None
            }
        }


class ChangePlanRequest(BaseModel):
    plan_id: str
    billing_cycle: BillingCycleEnum
    reset_period: bool = Field(False, description="Reset billing period to now")


class ChangeStatusRequest(BaseModel):
    status: SubscriptionStatusEnum
    reason: Optional[str] = None


class UpdateSeatsRequest(BaseModel):
    seat_count: int = Field(..., ge=1)
    billable_seats: Optional[int] = Field(None, ge=1, description="Override billable seats directly")


class UpdateAILimitRequest(BaseModel):
    queries_limit: int = Field(..., ge=0, description="New monthly AI query limit")
    extra_queries: Optional[int] = Field(None, ge=0, description="Override extra purchased queries")


class CreateSubscriptionRequest(BaseModel):
    plan_id: str
    billing_cycle: BillingCycleEnum
    seat_count: int = Field(..., ge=1)
    status: SubscriptionStatusEnum = SubscriptionStatusEnum.ACTIVE
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None


# ─── Plan ─────────────────────────────────────────────────────────────────────

class PlanCreateRequest(BaseModel):
    name: str
    plan_key: str
    price_per_user_monthly: Decimal = Field(..., ge=0)
    price_per_user_yearly: Decimal = Field(..., ge=0)
    minimum_seats: int = Field(1, ge=1)
    ai_queries_limit: int = Field(0, ge=0)
    features: Optional[dict] = None
    is_active: bool = True


class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    price_per_user_monthly: Optional[Decimal] = Field(None, ge=0)
    price_per_user_yearly: Optional[Decimal] = Field(None, ge=0)
    minimum_seats: Optional[int] = Field(None, ge=1)
    ai_queries_limit: Optional[int] = Field(None, ge=0)
    features: Optional[dict] = None
    is_active: Optional[bool] = None


class PlanResponse(BaseModel):
    id: str
    name: str
    plan_key: str
    price_per_user_monthly: Decimal
    price_per_user_yearly: Decimal
    minimum_seats: int
    ai_queries_limit: int
    features: Optional[dict]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductModuleItem(BaseModel):
    """One selectable module for plan features (matches implemented API areas)."""

    key: str
    label: str
    description: str
    category: str


class PricingPlaybookResponse(BaseModel):
    currency: str
    assumptions: str
    margin_target_percent: str
    sales_notes: List[str]


class PlanModulesCatalogResponse(BaseModel):
    """
    Catalog for superadmin UI: module checklist + pricing sanity checks.
    Use `feature_keys` / `default_features` when building plan feature toggles.
    """

    modules: List[ProductModuleItem]
    feature_keys: List[str]
    default_features: dict
    pricing_playbook: PricingPlaybookResponse
    pricing_floor_for_ai_limit: Optional[dict] = Field(
        default=None,
        description="Populated when ai_queries_limit query param is passed — min price hint vs AI usage",
    )


# ─── Stats ────────────────────────────────────────────────────────────────────

class PlatformStatsResponse(BaseModel):
    total_companies: int
    active_companies: int
    inactive_companies: int
    total_subscriptions: int
    active_subscriptions: int
    trial_subscriptions: int
    expired_subscriptions: int
    cancelled_subscriptions: int
    total_employees: int
    total_revenue_monthly: Decimal
    plans: List[dict]


# ─── Generic ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    success: bool = True
    message: str
