"""
Webhook Handlers for Third-party Services
"""
from fastapi import APIRouter, Request, HTTPException, status, Header, Depends
from sqlalchemy.orm import Session
import logging
import json
from datetime import timedelta

from app.db.session import get_database_session
from app.api.v1.services.razorpay_service import razorpay_service
from app.api.v1.services.subscription_service import SubscriptionService
from app.api.v1.models.subscription_model import SubscriptionStatus, BillingCycle
from app.api.v1.models.company_model import Company
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
    db: Session = Depends(get_database_session)
):
    """
    Handle Razorpay webhook events.
    
    Events handled:
    - subscription.activated
    - subscription.charged
    - invoice.paid
    - invoice.failed
    - subscription.cancelled
    - payment.captured
    """
    try:
        # Get raw body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Verify webhook signature
        is_valid = razorpay_service.verify_webhook_signature(
            payload=body_str,
            signature=x_razorpay_signature
        )
        
        if not is_valid:
            logger.warning("Invalid Razorpay webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse webhook payload
        payload = json.loads(body_str)
        event = payload.get("event")
        payload_data = payload.get("payload", {}).get("subscription", {}) or payload.get("payload", {}).get("payment", {}) or payload.get("payload", {})
        
        logger.info(f"Razorpay webhook received: {event}")
        
        # Handle different event types
        if event == "subscription.activated":
            await handle_subscription_activated(db, payload_data)
        elif event == "subscription.charged":
            await handle_subscription_charged(db, payload_data)
        elif event == "invoice.paid":
            await handle_invoice_paid(db, payload_data)
        elif event == "invoice.failed":
            await handle_invoice_failed(db, payload_data)
        elif event == "subscription.cancelled":
            await handle_subscription_cancelled(db, payload_data)
        elif event == "payment.captured":
            await handle_payment_captured(db, payload_data)
        else:
            logger.info(f"Unhandled Razorpay webhook event: {event}")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


async def handle_subscription_activated(db: Session, payload: dict):
    """Handle subscription.activated event"""
    subscription_id = payload.get("id")
    if not subscription_id:
        return
    
    # Find subscription by Razorpay ID
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.razorpay_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = datetime.utcnow()
        # Calculate period end based on billing cycle
        if subscription.billing_cycle == BillingCycle.MONTHLY:
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
        else:
            subscription.current_period_end = datetime.utcnow() + timedelta(days=365)
        db.commit()
        logger.info(f"Subscription activated: {subscription_id}")


async def handle_subscription_charged(db: Session, payload: dict):
    """Handle subscription.charged event"""
    subscription_id = payload.get("id")
    if not subscription_id:
        return
    
    # Update subscription period
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.razorpay_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.current_period_start = datetime.utcnow()
        if subscription.billing_cycle == BillingCycle.MONTHLY:
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
        else:
            subscription.current_period_end = datetime.utcnow() + timedelta(days=365)
        db.commit()
        logger.info(f"Subscription charged: {subscription_id}")


async def handle_invoice_paid(db: Session, payload: dict):
    """Handle invoice.paid event"""
    subscription_id = payload.get("subscription_id")
    if not subscription_id:
        return
    
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.razorpay_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.ACTIVE
        db.commit()
        logger.info(f"Invoice paid for subscription: {subscription_id}")


async def handle_invoice_failed(db: Session, payload: dict):
    """Handle invoice.failed event"""
    subscription_id = payload.get("subscription_id")
    if not subscription_id:
        return
    
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.razorpay_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.PAST_DUE
        db.commit()
        logger.warning(f"Invoice failed for subscription: {subscription_id}")


async def handle_subscription_cancelled(db: Session, payload: dict):
    """Handle subscription.cancelled event"""
    subscription_id = payload.get("id")
    if not subscription_id:
        return
    
    subscription = db.query(CompanySubscription).filter(
        CompanySubscription.razorpay_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        db.commit()
        logger.info(f"Subscription cancelled: {subscription_id}")


async def handle_payment_captured(db: Session, payload: dict):
    """Handle payment.captured event (for one-time payments like AI add-ons)"""
    payment_id = payload.get("id")
    order_id = payload.get("order_id")
    
    if not payment_id or not order_id:
        return
    
    # AI add-ons are handled via the verify endpoint, but we can log here
    logger.info(f"Payment captured: {payment_id} for order: {order_id}")

