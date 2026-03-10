"""
Subscription Management Service
Handles subscription creation, updates, billing calculations, and seat management
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import uuid

from app.api.v1.models.subscription_model import (
    SubscriptionPlan, CompanySubscription, SubscriptionUsage,
    AIUsage, CompanyAIUsage, AIAddon, BillingCycle, SubscriptionStatus, AIAddonType
)
from app.api.v1.models.company_model import Company
from app.api.v1.models.employee_model import Employee
from app.api.v1.services.razorpay_service import razorpay_service
from app.api.v1.utils.error_handler import raise_http_exception

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions"""
    
    @staticmethod
    def calculate_billable_seats(seat_count: int, minimum_seats: int) -> int:
        """
        Calculate billable seats based on minimum seat requirement.
        
        Formula: billable_seats = max(seat_count, minimum_seats)
        """
        return max(seat_count, minimum_seats)
    
    @staticmethod
    def calculate_monthly_cost(billable_seats: int, price_per_user: Decimal) -> Decimal:
        """Calculate monthly cost"""
        return Decimal(billable_seats) * price_per_user
    
    @staticmethod
    def get_price_per_user(plan: SubscriptionPlan, billing_cycle: BillingCycle) -> Decimal:
        """Get price per user based on billing cycle"""
        if billing_cycle == BillingCycle.MONTHLY:
            return plan.price_per_user_monthly
        else:
            return plan.price_per_user_yearly
    
    @staticmethod
    def get_all_plans(db: Session) -> List[SubscriptionPlan]:
        """Get all active subscription plans"""
        return db.query(SubscriptionPlan).filter(
            SubscriptionPlan.is_active == True
        ).order_by(SubscriptionPlan.price_per_user_monthly).all()
    
    @staticmethod
    def get_plan_by_id(db: Session, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID"""
        try:
            plan_uuid = uuid.UUID(plan_id)
        except ValueError:
            return None
        
        return db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == plan_uuid,
            SubscriptionPlan.is_active == True
        ).first()
    
    @staticmethod
    def get_company_subscription(db: Session, company_id: int) -> Optional[CompanySubscription]:
        """Get company's active subscription"""
        return db.query(CompanySubscription).filter(
            and_(
                CompanySubscription.company_id == company_id,
                CompanySubscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PAST_DUE
                ])
            )
        ).options(
            joinedload(CompanySubscription.plan)
        ).first()
    
    @staticmethod
    def create_subscription(
        db: Session,
        company_id: int,
        plan_id: str,
        billing_cycle: BillingCycle,
        seat_count: int,
        razorpay_customer_id: Optional[str] = None
    ) -> CompanySubscription:
        """
        Create a new subscription for a company.
        
        Note: In production, you would create Razorpay plan first, then subscribe.
        For now, we'll create the subscription record and handle Razorpay integration separately.
        """
        # Get plan
        plan = SubscriptionService.get_plan_by_id(db, plan_id)
        if not plan:
            raise_http_exception(
                message="Subscription plan not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="PLAN_NOT_FOUND"
            )
        
        # Check if company already has active subscription
        existing = SubscriptionService.get_company_subscription(db, company_id)
        if existing:
            raise_http_exception(
                message="Company already has an active subscription",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="SUBSCRIPTION_EXISTS"
            )
        
        # Calculate billable seats
        billable_seats = SubscriptionService.calculate_billable_seats(seat_count, plan.minimum_seats)
        
        # Get price per user
        price_per_user = SubscriptionService.get_price_per_user(plan, billing_cycle)
        
        # Calculate billing period
        now = datetime.utcnow()
        if billing_cycle == BillingCycle.MONTHLY:
            period_end = now + timedelta(days=30)
        else:
            period_end = now + timedelta(days=365)
        
        # Create subscription
        subscription = CompanySubscription(
            company_id=company_id,
            plan_id=plan.id,
            billing_cycle=billing_cycle,
            seat_count=seat_count,
            billable_seats=billable_seats,
            price_per_user=price_per_user,
            razorpay_customer_id=razorpay_customer_id,
            status=SubscriptionStatus.ACTIVE,  # Start as active (no trial)
            current_period_start=now,
            current_period_end=period_end,
            trial_end=None  # No trial period
        )
        
        db.add(subscription)
        db.flush()  # ensure subscription.id is available
        
        # Create or update subscription usage record for this company
        usage = db.query(SubscriptionUsage).filter(
            SubscriptionUsage.company_id == company_id
        ).first()

        if not usage:
            # No usage record yet → create one and link to subscription
            usage = SubscriptionUsage(
                company_id=company_id,
                subscription_id=subscription.id,
                employees_used=0,
                billable_seats=billable_seats,
            )
            db.add(usage)
        else:
            # Usage record exists (from previous subscription) → relink and reset
            usage.subscription_id = subscription.id
            usage.billable_seats = billable_seats
            usage.employees_used = 0
            usage.updated_at = datetime.utcnow()
        
        # Create or update initial AI usage record for current month
        now_dt = datetime.now()
        ai_usage = db.query(CompanyAIUsage).filter(
            and_(
                CompanyAIUsage.company_id == company_id,
                CompanyAIUsage.year == now_dt.year,
                CompanyAIUsage.month == now_dt.month,
            )
        ).first()

        if not ai_usage:
            # No record yet for this month → create one
            ai_usage = CompanyAIUsage(
                company_id=company_id,
                year=now_dt.year,
                month=now_dt.month,
                queries_used=0,
                queries_limit=plan.ai_queries_limit,
                extra_queries_purchased=0,
            )
            db.add(ai_usage)
        else:
            # Record already exists → just ensure the limit matches the plan
            ai_usage.queries_limit = plan.ai_queries_limit
        
        db.commit()
        db.refresh(subscription)
        
        logger.info(f"Subscription created for company {company_id}: {subscription.id}")
        return subscription
    
    @staticmethod
    def update_subscription_seats(
        db: Session,
        company_id: int,
        new_seat_count: int
    ) -> CompanySubscription:
        """Update subscription seat count"""
        subscription = SubscriptionService.get_company_subscription(db, company_id)
        if not subscription:
            raise_http_exception(
                message="No active subscription found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SUBSCRIPTION_NOT_FOUND"
            )
        
        # Calculate new billable seats
        new_billable_seats = SubscriptionService.calculate_billable_seats(
            new_seat_count,
            subscription.plan.minimum_seats
        )
        
        # Update subscription
        subscription.seat_count = new_seat_count
        subscription.billable_seats = new_billable_seats
        subscription.updated_at = datetime.utcnow()
        
        # Update usage record
        usage = db.query(SubscriptionUsage).filter(
            SubscriptionUsage.company_id == company_id
        ).first()
        if usage:
            usage.billable_seats = new_billable_seats
            usage.updated_at = datetime.utcnow()
        
        # Update Razorpay subscription if exists
        if subscription.razorpay_subscription_id:
            try:
                razorpay_service.update_subscription_quantity(
                    subscription.razorpay_subscription_id,
                    new_billable_seats
                )
            except Exception as e:
                logger.error(f"Failed to update Razorpay subscription: {e}")
                # Continue with local update even if Razorpay fails
        
        db.commit()
        db.refresh(subscription)
        
        logger.info(f"Subscription seats updated for company {company_id}: {new_billable_seats}")
        return subscription
    
    @staticmethod
    def cancel_subscription(
        db: Session,
        company_id: int,
        cancel_at_period_end: bool = True
    ) -> CompanySubscription:
        """Cancel subscription"""
        subscription = SubscriptionService.get_company_subscription(db, company_id)
        if not subscription:
            raise_http_exception(
                message="No active subscription found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SUBSCRIPTION_NOT_FOUND"
            )
        
        subscription.cancel_at_period_end = cancel_at_period_end
        subscription.cancelled_at = datetime.utcnow() if not cancel_at_period_end else None
        
        if not cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED
        
        # Cancel Razorpay subscription if exists
        if subscription.razorpay_subscription_id:
            try:
                razorpay_service.cancel_subscription(
                    subscription.razorpay_subscription_id,
                    cancel_at_period_end
                )
            except Exception as e:
                logger.error(f"Failed to cancel Razorpay subscription: {e}")
        
        db.commit()
        db.refresh(subscription)
        
        logger.info(f"Subscription cancelled for company {company_id}")
        return subscription
    
    @staticmethod
    def sync_employee_count(db: Session, company_id: int) -> SubscriptionUsage:
        """Sync employee count with subscription usage"""
        # Count active employees
        employee_count = db.query(func.count(Employee.id)).filter(
            and_(
                Employee.company_id == company_id,
                Employee.status == "active"  # Assuming status field exists
            )
        ).scalar() or 0
        
        # Get subscription
        subscription = SubscriptionService.get_company_subscription(db, company_id)
        if not subscription:
            raise_http_exception(
                message="No active subscription found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SUBSCRIPTION_NOT_FOUND"
            )
        
        # Get or create usage record
        usage = db.query(SubscriptionUsage).filter(
            SubscriptionUsage.company_id == company_id
        ).first()
        
        if not usage:
            usage = SubscriptionUsage(
                company_id=company_id,
                employees_used=employee_count,
                billable_seats=subscription.billable_seats
            )
            db.add(usage)
        else:
            usage.employees_used = employee_count
            usage.billable_seats = subscription.billable_seats
            usage.last_synced_at = datetime.utcnow()
            usage.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(usage)
        
        return usage
    
    @staticmethod
    def check_seat_availability(db: Session, company_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if company can add more employees.
        
        Returns:
            (can_add, error_message)
        """
        subscription = SubscriptionService.get_company_subscription(db, company_id)
        if not subscription:
            return False, "No active subscription found"
        
        # Sync employee count
        usage = SubscriptionService.sync_employee_count(db, company_id)
        
        # Check if employees_used < billable_seats
        if usage.employees_used >= usage.billable_seats:
            return False, f"Seat limit reached. Current: {usage.employees_used}/{usage.billable_seats}. Please upgrade your plan or increase seats."
        
        return True, None
    
    @staticmethod
    def get_current_subscription_info(db: Session, company_id: int) -> dict:
        """Get current subscription information for dashboard"""
        subscription = SubscriptionService.get_company_subscription(db, company_id)
        if not subscription:
            return {
                "plan": None,
                "plan_key": None,
                "employees_used": 0,
                "billable_seats": 0,
                "price_per_user": Decimal(0),
                "monthly_cost": Decimal(0),
                "billing_cycle": None,
                "ai_usage": 0,
                "ai_limit": 0,
                "ai_remaining": 0,
                "next_billing_date": None,
                "status": None
            }
        
        # Get usage
        usage = db.query(SubscriptionUsage).filter(
            SubscriptionUsage.company_id == company_id
        ).first()
        
        employees_used = usage.employees_used if usage else 0
        
        # Calculate monthly cost
        monthly_cost = SubscriptionService.calculate_monthly_cost(
            subscription.billable_seats,
            subscription.price_per_user
        )
        
        # Get AI usage for current month
        now_dt = datetime.now()
        ai_usage_record = db.query(CompanyAIUsage).filter(
            and_(
                CompanyAIUsage.company_id == company_id,
                CompanyAIUsage.year == now_dt.year,
                CompanyAIUsage.month == now_dt.month
            )
        ).first()
        
        ai_used = ai_usage_record.queries_used if ai_usage_record else 0
        ai_limit = ai_usage_record.total_limit if ai_usage_record else subscription.plan.ai_queries_limit
        ai_remaining = ai_usage_record.remaining_queries if ai_usage_record else ai_limit
        
        return {
            "plan": subscription.plan.name,
            "plan_key": subscription.plan.plan_key,
            "employees_used": employees_used,
            "billable_seats": subscription.billable_seats,
            "price_per_user": subscription.price_per_user,
            "monthly_cost": monthly_cost,
            "billing_cycle": subscription.billing_cycle,
            "ai_usage": ai_used,
            "ai_limit": ai_limit,
            "ai_remaining": ai_remaining,
            "next_billing_date": subscription.current_period_end,
            "status": subscription.status
        }
    
    @staticmethod
    def purchase_ai_addon(
        db: Session,
        company_id: int,
        addon_type: AIAddonType,
        razorpay_payment_id: Optional[str] = None,
        razorpay_order_id: Optional[str] = None
    ) -> AIAddon:
        """Purchase AI add-on"""
        # Define add-on details
        addon_details = {
            AIAddonType.AI_1000_PACK: {
                "queries": 1000,
                "price": Decimal("199.00")
            },
            AIAddonType.AI_5000_PACK: {
                "queries": 5000,
                "price": Decimal("799.00")
            }
        }
        
        if addon_type not in addon_details:
            raise_http_exception(
                message="Invalid add-on type",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_ADDON_TYPE"
            )
        
        details = addon_details[addon_type]
        
        # Get current month AI usage
        now_dt = datetime.now()
        ai_usage = db.query(CompanyAIUsage).filter(
            and_(
                CompanyAIUsage.company_id == company_id,
                CompanyAIUsage.year == now_dt.year,
                CompanyAIUsage.month == now_dt.month
            )
        ).first()
        
        if not ai_usage:
            # Create if doesn't exist
            subscription = SubscriptionService.get_company_subscription(db, company_id)
            if not subscription:
                raise_http_exception(
                    message="No active subscription found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="SUBSCRIPTION_NOT_FOUND"
                )
            
            ai_usage = CompanyAIUsage(
                company_id=company_id,
                year=now_dt.year,
                month=now_dt.month,
                queries_used=0,
                queries_limit=subscription.plan.ai_queries_limit,
                extra_queries_purchased=0
            )
            db.add(ai_usage)
            db.flush()
        
        # Add queries
        ai_usage.extra_queries_purchased += details["queries"]
        ai_usage.updated_at = datetime.utcnow()
        
        # Create addon record
        addon = AIAddon(
            company_id=company_id,
            addon_type=addon_type,
            queries_added=details["queries"],
            price=details["price"],
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            applied_to_month=now_dt.month,
            applied_to_year=now_dt.year
        )
        db.add(addon)
        
        db.commit()
        db.refresh(addon)
        
        logger.info(f"AI add-on purchased for company {company_id}: {addon_type.value}")
        return addon
    
    @staticmethod
    def check_ai_usage_limit(db: Session, company_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if company can make AI queries.
        
        Returns:
            (can_query, error_message)
        """
        subscription = SubscriptionService.get_company_subscription(db, company_id)
        if not subscription:
            return False, "No active subscription found"
        
        # Get current month AI usage
        now_dt = datetime.now()
        ai_usage = db.query(CompanyAIUsage).filter(
            and_(
                CompanyAIUsage.company_id == company_id,
                CompanyAIUsage.year == now_dt.year,
                CompanyAIUsage.month == now_dt.month
            )
        ).first()
        
        if not ai_usage:
            # Create if doesn't exist
            ai_usage = CompanyAIUsage(
                company_id=company_id,
                year=now_dt.year,
                month=now_dt.month,
                queries_used=0,
                queries_limit=subscription.plan.ai_queries_limit,
                extra_queries_purchased=0
            )
            db.add(ai_usage)
            db.commit()
            db.refresh(ai_usage)
        
        # Check limit
        if ai_usage.queries_used >= ai_usage.total_limit:
            return False, f"AI usage limit reached. Used: {ai_usage.queries_used}/{ai_usage.total_limit}. Please purchase an add-on to increase your limit."
        
        return True, None
    
    @staticmethod
    def record_ai_usage(
        db: Session,
        company_id: int,
        user_id: Optional[int],
        tokens_used: int,
        question: Optional[str] = None
    ) -> AIUsage:
        """Record AI query usage"""
        # Get current month AI usage
        now_dt = datetime.now()
        ai_usage = db.query(CompanyAIUsage).filter(
            and_(
                CompanyAIUsage.company_id == company_id,
                CompanyAIUsage.year == now_dt.year,
                CompanyAIUsage.month == now_dt.month
            )
        ).first()
        
        if not ai_usage:
            # Create if doesn't exist
            subscription = SubscriptionService.get_company_subscription(db, company_id)
            if not subscription:
                raise_http_exception(
                    message="No active subscription found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="SUBSCRIPTION_NOT_FOUND"
                )
            
            ai_usage = CompanyAIUsage(
                company_id=company_id,
                year=now_dt.year,
                month=now_dt.month,
                queries_used=0,
                queries_limit=subscription.plan.ai_queries_limit,
                extra_queries_purchased=0
            )
            db.add(ai_usage)
            db.flush()
        
        # Increment query count (1 query per API call)
        ai_usage.queries_used += 1
        ai_usage.updated_at = datetime.utcnow()
        
        # Create usage record
        usage_record = AIUsage(
            company_id=company_id,
            user_id=user_id,
            question=question,
            tokens_used=tokens_used
        )
        db.add(usage_record)
        
        db.commit()
        db.refresh(usage_record)
        
        return usage_record

