"""
Subscription and Billing Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Numeric, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.db.base import Base


class BillingCycle(str, enum.Enum):
    """Billing cycle enumeration"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enumeration"""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AIAddonType(str, enum.Enum):
    """AI add-on type enumeration"""
    AI_1000_PACK = "AI_1000_PACK"  # +1000 queries for ₹199
    AI_5000_PACK = "AI_5000_PACK"  # +5000 queries for ₹799


class SubscriptionPlan(Base):
    """
    Subscription plan definitions.
    """
    __tablename__ = "subscription_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)  # Starter, Growth, Scale
    plan_key = Column(String(50), nullable=False, unique=True, index=True)  # starter, growth, scale
    price_per_user_monthly = Column(Numeric(10, 2), nullable=False)  # Price in INR
    price_per_user_yearly = Column(Numeric(10, 2), nullable=False)  # Price in INR (with 20% discount)
    minimum_seats = Column(Integer, nullable=False, default=1)
    ai_queries_limit = Column(Integer, nullable=False, default=0)  # Monthly AI query limit
    features = Column(JSONB, nullable=True)  # JSON object with feature flags
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("CompanySubscription", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan {self.name}>"


class CompanySubscription(Base):
    """
    Company subscription records.
    Each company has one active subscription.
    """
    __tablename__ = "company_subscriptions"
    __table_args__ = (
        Index('idx_company_subscription_active', 'company_id', 'status'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    billing_cycle = Column(Enum(BillingCycle), nullable=False)
    seat_count = Column(Integer, nullable=False)  # Requested seat count
    billable_seats = Column(Integer, nullable=False)  # Actual billable seats (max(seat_count, minimum_seats))
    price_per_user = Column(Numeric(10, 2), nullable=False)  # Price per user based on billing cycle
    razorpay_subscription_id = Column(String(255), nullable=True, unique=True, index=True)  # Razorpay subscription ID
    razorpay_customer_id = Column(String(255), nullable=True, index=True)  # Razorpay customer ID
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False, index=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)  # Trial end date
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    usage = relationship("SubscriptionUsage", back_populates="subscription", uselist=False, foreign_keys="[SubscriptionUsage.subscription_id]")
    
    def __repr__(self):
        return f"<CompanySubscription Company:{self.company_id} Plan:{self.plan_id} Status:{self.status.value}>"


class SubscriptionUsage(Base):
    """
    Tracks seat usage for subscriptions.
    """
    __tablename__ = "subscription_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("company_subscriptions.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    employees_used = Column(Integer, nullable=False, default=0)  # Current number of employees
    billable_seats = Column(Integer, nullable=False, default=0)  # Current billable seats
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("CompanySubscription", back_populates="usage", foreign_keys=[subscription_id])
    
    def __repr__(self):
        return f"<SubscriptionUsage Company:{self.company_id} Employees:{self.employees_used} Billable:{self.billable_seats}>"


class AIUsage(Base):
    """
    Tracks individual AI query usage.
    """
    __tablename__ = "ai_usage"
    __table_args__ = (
        Index('idx_ai_usage_company_created', 'company_id', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    question = Column(Text, nullable=True)  # Store question for analytics (optional)
    tokens_used = Column(Integer, nullable=False, default=0)  # Tokens consumed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    company = relationship("Company")
    user = relationship("User")
    
    def __repr__(self):
        return f"<AIUsage Company:{self.company_id} Tokens:{self.tokens_used}>"


class CompanyAIUsage(Base):
    """
    Monthly AI usage summary per company.
    """
    __tablename__ = "company_ai_usage"
    __table_args__ = (
        UniqueConstraint('company_id', 'year', 'month', name='uq_company_ai_usage_month'),
        Index('idx_company_ai_usage_company_month', 'company_id', 'year', 'month'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    queries_used = Column(Integer, nullable=False, default=0)  # Number of queries used this month
    queries_limit = Column(Integer, nullable=False, default=0)  # Base limit from subscription plan
    extra_queries_purchased = Column(Integer, nullable=False, default=0)  # Additional queries from add-ons
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    
    @property
    def total_limit(self) -> int:
        """Total AI queries limit (base + add-ons)"""
        return self.queries_limit + self.extra_queries_purchased
    
    @property
    def remaining_queries(self) -> int:
        """Remaining queries for the month"""
        return max(0, self.total_limit - self.queries_used)
    
    def __repr__(self):
        return f"<CompanyAIUsage Company:{self.company_id} {self.year}-{self.month:02d} Used:{self.queries_used}/{self.total_limit}>"


class AIAddon(Base):
    """
    AI add-on purchases.
    """
    __tablename__ = "ai_addons"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    addon_type = Column(Enum(AIAddonType), nullable=False)
    queries_added = Column(Integer, nullable=False)  # Number of queries added
    price = Column(Numeric(10, 2), nullable=False)  # Price paid in INR
    razorpay_payment_id = Column(String(255), nullable=True, index=True)  # Razorpay payment ID
    razorpay_order_id = Column(String(255), nullable=True, index=True)  # Razorpay order ID
    applied_to_month = Column(Integer, nullable=False)  # Month (1-12) when add-on is applied
    applied_to_year = Column(Integer, nullable=False)  # Year when add-on is applied
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    
    def __repr__(self):
        return f"<AIAddon Company:{self.company_id} Type:{self.addon_type.value} Queries:{self.queries_added}>"

