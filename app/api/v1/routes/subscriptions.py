"""
Subscription Management API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
import logging

from app.db.session import get_database_session
from app.api.v1.schemas.subscription_schema import (
    SubscriptionPlanResponse,
    SubscriptionCreateRequest,
    SubscriptionUpdateSeatsRequest,
    SubscriptionResponse,
    CurrentSubscriptionResponse,
    AIAddonPurchaseRequest,
    RazorpayOrderResponse,
    MessageResponse
)
from app.api.v1.services.subscription_service import SubscriptionService
from app.api.v1.services.razorpay_service import razorpay_service
from app.api.v1.dependencies import get_current_authenticated_user
from app.api.v1.models.user_model import User
from app.api.v1.models.subscription_model import AIAddonType
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    db: Session = Depends(get_database_session)
):
    """
    Get all available subscription plans.
    """
    plans = SubscriptionService.get_all_plans(db)
    return [SubscriptionPlanResponse.model_validate(plan) for plan in plans]


@router.post("/create", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: Request,
    subscription_data: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new subscription for the company.
    Only admins can create subscriptions.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create subscriptions"
        )
    
    try:
        # Get company
        company = current_user.company
        
        # Create Razorpay customer if not exists
        razorpay_customer_id = None
        if razorpay_service.client:
            try:
                customer = razorpay_service.create_customer(
                    name=company.company_name,
                    email=company.email,
                    contact=company.phone
                )
                razorpay_customer_id = customer["id"]
            except Exception as e:
                logger.warning(f"Failed to create Razorpay customer: {e}")
                # Continue without Razorpay customer for now
        
        # Create subscription
        subscription = SubscriptionService.create_subscription(
            db=db,
            company_id=current_user.company_id,
            plan_id=subscription_data.plan_id,
            billing_cycle=subscription_data.billing_cycle,
            seat_count=subscription_data.seat_count,
            razorpay_customer_id=razorpay_customer_id
        )
        
        # Load plan relationship
        db.refresh(subscription)
        
        # Calculate monthly cost
        monthly_cost = SubscriptionService.calculate_monthly_cost(
            subscription.billable_seats,
            subscription.price_per_user
        )
        
        response = SubscriptionResponse(
            id=str(subscription.id),
            company_id=subscription.company_id,
            plan=SubscriptionPlanResponse.model_validate(subscription.plan),
            billing_cycle=subscription.billing_cycle,
            seat_count=subscription.seat_count,
            billable_seats=subscription.billable_seats,
            price_per_user=subscription.price_per_user,
            monthly_cost=monthly_cost,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_end=subscription.trial_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            razorpay_subscription_id=subscription.razorpay_subscription_id,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.patch("/update-seats", response_model=SubscriptionResponse)
async def update_subscription_seats(
    request: Request,
    seat_data: SubscriptionUpdateSeatsRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update subscription seat count.
    Only admins can update seats.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update subscription seats"
        )
    
    try:
        subscription = SubscriptionService.update_subscription_seats(
            db=db,
            company_id=current_user.company_id,
            new_seat_count=seat_data.seat_count
        )
        
        # Load plan relationship
        db.refresh(subscription)
        
        # Calculate monthly cost
        monthly_cost = SubscriptionService.calculate_monthly_cost(
            subscription.billable_seats,
            subscription.price_per_user
        )
        
        return SubscriptionResponse(
            id=str(subscription.id),
            company_id=subscription.company_id,
            plan=SubscriptionPlanResponse.model_validate(subscription.plan),
            billing_cycle=subscription.billing_cycle,
            seat_count=subscription.seat_count,
            billable_seats=subscription.billable_seats,
            price_per_user=subscription.price_per_user,
            monthly_cost=monthly_cost,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_end=subscription.trial_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            razorpay_subscription_id=subscription.razorpay_subscription_id,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription seats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription seats: {str(e)}"
        )


@router.post("/cancel", response_model=MessageResponse)
async def cancel_subscription(
    request: Request,
    cancel_at_period_end: bool = True,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Cancel subscription.
    Only admins can cancel subscriptions.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can cancel subscriptions"
        )
    
    try:
        SubscriptionService.cancel_subscription(
            db=db,
            company_id=current_user.company_id,
            cancel_at_period_end=cancel_at_period_end
        )
        
        message = "Subscription cancelled" if not cancel_at_period_end else "Subscription will be cancelled at period end"
        return MessageResponse(message=message, success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.get("/current", response_model=CurrentSubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get current subscription information for dashboard.
    """
    try:
        info = SubscriptionService.get_current_subscription_info(
            db=db,
            company_id=current_user.company_id
        )
        
        return CurrentSubscriptionResponse(**info)
        
    except Exception as e:
        logger.error(f"Error getting current subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription info: {str(e)}"
        )


@router.post("/ai-addon/order", response_model=RazorpayOrderResponse)
async def create_ai_addon_order(
    request: Request,
    addon_data: AIAddonPurchaseRequest,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create Razorpay order for AI add-on purchase.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can purchase AI add-ons"
        )
    
    # Define add-on prices
    addon_prices = {
        AIAddonType.AI_1000_PACK: 199.00,
        AIAddonType.AI_5000_PACK: 799.00
    }
    
    if addon_data.addon_type not in addon_prices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid add-on type"
        )
    
    price = addon_prices[addon_data.addon_type]
    
    try:
        # Create Razorpay order
        order = razorpay_service.create_order(
            amount=price,
            currency="INR",
            receipt=f"ai_addon_{current_user.company_id}_{addon_data.addon_type.value}",
            notes={
                "company_id": current_user.company_id,
                "addon_type": addon_data.addon_type.value
            }
        )
        
        return RazorpayOrderResponse(
            order_id=order["id"],
            amount=price,
            currency="INR",
            key=settings.RAZORPAY_KEY_ID or ""
        )
        
    except Exception as e:
        logger.error(f"Error creating AI add-on order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.post("/ai-addon/verify", response_model=MessageResponse)
async def verify_ai_addon_payment(
    request: Request,
    payment_id: str,
    order_id: str,
    signature: str,
    addon_type: AIAddonType,
    current_user: User = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Verify AI add-on payment and apply to subscription.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can verify AI add-on payments"
        )
    
    try:
        # Verify payment signature
        is_valid = razorpay_service.verify_payment_signature(
            payment_id=payment_id,
            order_id=order_id,
            signature=signature
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature"
            )
        
        # Purchase add-on
        addon = SubscriptionService.purchase_ai_addon(
            db=db,
            company_id=current_user.company_id,
            addon_type=addon_type,
            razorpay_payment_id=payment_id,
            razorpay_order_id=order_id
        )
        
        return MessageResponse(
            message=f"AI add-on purchased successfully. {addon.queries_added} queries added.",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying AI add-on payment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify payment: {str(e)}"
        )

