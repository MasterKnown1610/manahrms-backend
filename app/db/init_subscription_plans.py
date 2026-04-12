"""
Initialize Subscription Plans in Database
Run this script to create default subscription plans
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.api.v1.models.subscription_model import SubscriptionPlan
from app.api.v1.constants.product_modules import default_features_all_false
import logging

logger = logging.getLogger(__name__)


def init_subscription_plans():
    """Initialize default subscription plans"""
    db: Session = SessionLocal()
    
    try:
        # Check if plans already exist
        existing_plans = db.query(SubscriptionPlan).count()
        if existing_plans > 0:
            logger.info(f"Subscription plans already exist ({existing_plans} plans found). Skipping initialization.")
            return
        
        def _all_modules(enabled: bool) -> dict:
            f = default_features_all_false()
            if enabled:
                for k in f:
                    f[k] = True
            return f

        # Feature keys must match app/api/v1/constants/product_modules.py (implemented API modules only).
        starter_features = _all_modules(True)
        starter_features["chat"] = False  # differentiate tier; superadmin can change via PATCH /plans

        growth_features = _all_modules(True)
        scale_features = _all_modules(True)

        # Create plans
        plans = [
            {
                "name": "Starter",
                "plan_key": "starter",
                "price_per_user_monthly": 49.00,
                "price_per_user_yearly": 470.00,  # 20% discount: 49 * 12 * 0.8 = 470.4 ≈ 470
                "minimum_seats": 1,
                "ai_queries_limit": 300,
                "features": starter_features,
            },
            {
                "name": "Growth",
                "plan_key": "growth",
                "price_per_user_monthly": 39.00,
                "price_per_user_yearly": 374.40,  # 20% discount: 39 * 12 * 0.8 = 374.4
                "minimum_seats": 10,
                "ai_queries_limit": 800,
                "features": growth_features,
            },
            {
                "name": "Scale",
                "plan_key": "scale",
                "price_per_user_monthly": 29.00,
                "price_per_user_yearly": 278.40,  # 20% discount: 29 * 12 * 0.8 = 278.4
                "minimum_seats": 25,
                "ai_queries_limit": 2000,
                "features": scale_features,
            },
        ]
        
        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)
        
        db.commit()
        logger.info(f"Successfully initialized {len(plans)} subscription plans")
        
    except Exception as e:
        logger.error(f"Error initializing subscription plans: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_subscription_plans()




