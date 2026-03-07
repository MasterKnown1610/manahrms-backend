"""
Razorpay Payment Gateway Service
"""
import razorpay
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta

from app.core.config import settings
from app.api.v1.models.subscription_model import BillingCycle

logger = logging.getLogger(__name__)


class RazorpayService:
    """Service for Razorpay payment gateway integration"""
    
    def __init__(self):
        """Initialize Razorpay client"""
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            logger.warning("Razorpay credentials not configured. Payment features will be disabled.")
            self.client = None
        else:
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            logger.info("Razorpay client initialized")
    
    def create_customer(self, name: str, email: str, contact: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Razorpay customer.
        
        Args:
            name: Customer name
            email: Customer email
            contact: Customer contact number (optional)
        
        Returns:
            Customer data from Razorpay
        """
        if not self.client:
            raise ValueError("Razorpay client not initialized. Please configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
        
        try:
            customer_data = {
                "name": name,
                "email": email,
            }
            if contact:
                customer_data["contact"] = contact
            
            customer = self.client.customer.create(data=customer_data)
            logger.info(f"Razorpay customer created: {customer['id']}")
            return customer
        except Exception as e:
            logger.error(f"Error creating Razorpay customer: {e}", exc_info=True)
            raise
    
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        quantity: int,
        billing_cycle: BillingCycle,
        start_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a Razorpay subscription.
        
        Args:
            customer_id: Razorpay customer ID
            plan_id: Razorpay plan ID
            quantity: Number of seats
            billing_cycle: Monthly or yearly
            start_at: Subscription start date (optional, defaults to now)
        
        Returns:
            Subscription data from Razorpay
        """
        if not self.client:
            raise ValueError("Razorpay client not initialized")
        
        try:
            # Calculate total amount
            # Note: In Razorpay, you typically create a plan first, then subscribe to it
            # For now, we'll create a subscription with item-based pricing
            
            subscription_data = {
                "plan_id": plan_id,
                "customer_notify": 1,
                "quantity": quantity,
                "total_count": 12 if billing_cycle == BillingCycle.YEARLY else 1,  # 12 months for yearly
                "start_at": int(start_at.timestamp()) if start_at else int(datetime.now().timestamp()),
            }
            
            subscription = self.client.subscription.create(data=subscription_data)
            logger.info(f"Razorpay subscription created: {subscription['id']}")
            return subscription
        except Exception as e:
            logger.error(f"Error creating Razorpay subscription: {e}", exc_info=True)
            raise
    
    def update_subscription_quantity(
        self,
        subscription_id: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Update subscription quantity (seats).
        
        Args:
            subscription_id: Razorpay subscription ID
            quantity: New quantity
        
        Returns:
            Updated subscription data
        """
        if not self.client:
            raise ValueError("Razorpay client not initialized")
        
        try:
            subscription = self.client.subscription.fetch(subscription_id)
            
            # Update subscription
            updated = self.client.subscription.update(
                subscription_id,
                {
                    "quantity": quantity
                }
            )
            logger.info(f"Razorpay subscription quantity updated: {subscription_id} -> {quantity}")
            return updated
        except Exception as e:
            logger.error(f"Error updating Razorpay subscription quantity: {e}", exc_info=True)
            raise
    
    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a Razorpay subscription.
        
        Args:
            subscription_id: Razorpay subscription ID
            cancel_at_period_end: Whether to cancel at period end or immediately
        
        Returns:
            Cancelled subscription data
        """
        if not self.client:
            raise ValueError("Razorpay client not initialized")
        
        try:
            if cancel_at_period_end:
                # Cancel at period end
                cancelled = self.client.subscription.update(
                    subscription_id,
                    {
                        "cancel_at_period_end": 1
                    }
                )
            else:
                # Cancel immediately
                cancelled = self.client.subscription.cancel(subscription_id)
            
            logger.info(f"Razorpay subscription cancelled: {subscription_id}")
            return cancelled
        except Exception as e:
            logger.error(f"Error cancelling Razorpay subscription: {e}", exc_info=True)
            raise
    
    def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order for one-time payments (e.g., AI add-ons).
        
        Args:
            amount: Amount in paise (multiply INR by 100)
            currency: Currency code (default: INR)
            receipt: Receipt ID (optional)
            notes: Additional notes (optional)
        
        Returns:
            Order data from Razorpay
        """
        if not self.client:
            raise ValueError("Razorpay client not initialized")
        
        try:
            # Convert Decimal to int (paise)
            amount_paise = int(amount * 100)
            
            order_data = {
                "amount": amount_paise,
                "currency": currency,
            }
            
            if receipt:
                order_data["receipt"] = receipt
            
            if notes:
                order_data["notes"] = notes
            
            order = self.client.order.create(data=order_data)
            logger.info(f"Razorpay order created: {order['id']}")
            return order
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {e}", exc_info=True)
            raise
    
    def verify_payment_signature(
        self,
        payment_id: str,
        order_id: str,
        signature: str
    ) -> bool:
        """
        Verify Razorpay payment signature.
        
        Args:
            payment_id: Payment ID from Razorpay
            order_id: Order ID
            signature: Signature to verify
        
        Returns:
            True if signature is valid
        """
        if not self.client:
            return False
        
        try:
            params = {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            }
            self.client.utility.verify_payment_signature(params)
            return True
        except Exception as e:
            logger.error(f"Payment signature verification failed: {e}")
            return False
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify Razorpay webhook signature.
        
        Args:
            payload: Webhook payload (string)
            signature: Webhook signature from headers
        
        Returns:
            True if signature is valid
        """
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.warning("Razorpay webhook secret not configured")
            return False
        
        try:
            self.client.utility.verify_webhook_signature(
                payload,
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
    
    def fetch_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Fetch subscription details from Razorpay"""
        if not self.client:
            raise ValueError("Razorpay client not initialized")
        
        try:
            return self.client.subscription.fetch(subscription_id)
        except Exception as e:
            logger.error(f"Error fetching Razorpay subscription: {e}", exc_info=True)
            raise


# Global instance
razorpay_service = RazorpayService()

