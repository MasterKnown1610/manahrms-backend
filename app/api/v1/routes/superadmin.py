"""
SuperAdmin API Routes
Full platform control: companies, subscriptions, plans, and stats.
Authentication: email + password → JWT with is_superadmin=True claim.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import logging

from app.db.session import get_database_session
from app.core.security import (
    hash_password_for_storage,
    verify_password_against_hash,
    create_jwt_access_token,
    decode_and_verify_jwt_token,
)
from app.core.config import settings
from app.api.v1.models.superadmin_model import SuperAdmin
from app.api.v1.models.company_model import Company
from app.api.v1.models.user_model import User
from app.api.v1.models.employee_model import Employee
from app.api.v1.models.subscription_model import (
    CompanySubscription,
    SubscriptionPlan,
    SubscriptionUsage,
    CompanyAIUsage,
    AIUsage,
    BillingCycle,
    SubscriptionStatus,
)
from app.api.v1.models.user_model import User as UserModel
from app.api.v1.schemas.superadmin_schema import (
    SuperAdminLogin,
    SuperAdminTokenResponse,
    SuperAdminResponse,
    CompanyBriefResponse,
    CompanyDetailResponse,
    CompanyUpdateRequest,
    SubscriptionDetailResponse,
    ExtendSubscriptionRequest,
    ChangePlanRequest,
    ChangeStatusRequest,
    UpdateSeatsRequest,
    UpdateAILimitRequest,
    CreateSubscriptionRequest,
    PlanCreateRequest,
    PlanUpdateRequest,
    PlanResponse,
    PlanModulesCatalogResponse,
    ProductModuleItem,
    PricingPlaybookResponse,
    PlatformStatsResponse,
    MessageResponse,
)
from app.api.v1.constants.product_modules import (
    PRODUCT_MODULES,
    MODULE_KEYS,
    default_features_all_false,
    sanitize_plan_features,
    list_unknown_feature_keys,
    estimate_pricing_floor,
    pricing_playbook_text,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/superadmin", tags=["SuperAdmin"])

# Separate OAuth2 scheme so superadmin tokens don't conflict with regular user tokens
superadmin_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/superadmin/login",
    scheme_name="SuperAdminOAuth2",
    auto_error=False,
)


# ─── Dependency ───────────────────────────────────────────────────────────────

def get_current_superadmin(
    token: str = Depends(superadmin_oauth2_scheme),
    db: Session = Depends(get_database_session),
) -> SuperAdmin:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Not authenticated", "error_code": "NOT_AUTHENTICATED"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_and_verify_jwt_token(token)
    if payload is None or not payload.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Invalid or expired token", "error_code": "INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_id = payload.get("admin_id")
    admin = db.query(SuperAdmin).filter(SuperAdmin.id == admin_id, SuperAdmin.is_active == True).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "SuperAdmin not found or inactive", "error_code": "ADMIN_NOT_FOUND"},
        )
    return admin


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_subscription_detail(db: Session, sub: CompanySubscription) -> dict:
    """Build subscription detail dict from ORM object."""
    usage = db.query(SubscriptionUsage).filter(SubscriptionUsage.company_id == sub.company_id).first()
    now_dt = datetime.now()
    ai_record = db.query(CompanyAIUsage).filter(
        and_(
            CompanyAIUsage.company_id == sub.company_id,
            CompanyAIUsage.year == now_dt.year,
            CompanyAIUsage.month == now_dt.month,
        )
    ).first()

    monthly_cost = Decimal(sub.billable_seats) * sub.price_per_user

    return {
        "id": str(sub.id),
        "company_id": sub.company_id,
        "company_name": sub.company.company_name if sub.company else "",
        "plan_name": sub.plan.name if sub.plan else "",
        "plan_key": sub.plan.plan_key if sub.plan else "",
        "billing_cycle": sub.billing_cycle.value if sub.billing_cycle else "",
        "seat_count": sub.seat_count,
        "billable_seats": sub.billable_seats,
        "price_per_user": sub.price_per_user,
        "monthly_cost": monthly_cost,
        "status": sub.status.value if sub.status else "",
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "trial_end": sub.trial_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "cancelled_at": sub.cancelled_at,
        "razorpay_subscription_id": sub.razorpay_subscription_id,
        "razorpay_customer_id": sub.razorpay_customer_id,
        "employees_used": usage.employees_used if usage else 0,
        "ai_queries_used": ai_record.queries_used if ai_record else 0,
        "ai_queries_limit": ai_record.total_limit if ai_record else (sub.plan.ai_queries_limit if sub.plan else 0),
        "created_at": sub.created_at,
        "updated_at": sub.updated_at,
    }


# ─── Auth ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=SuperAdminTokenResponse, summary="SuperAdmin Login")
async def superadmin_login(
    login_data: SuperAdminLogin,
    db: Session = Depends(get_database_session),
):
    """
    Login as a SuperAdmin using email and password.
    Returns a JWT token with `is_superadmin=true` claim.
    """
    admin = db.query(SuperAdmin).filter(SuperAdmin.email == login_data.email).first()

    if not admin or not verify_password_against_hash(login_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Invalid email or password", "error_code": "INVALID_CREDENTIALS"},
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "SuperAdmin account is inactive", "error_code": "ADMIN_INACTIVE"},
        )

    access_token = create_jwt_access_token(
        data={
            "sub": admin.username,
            "admin_id": admin.id,
            "is_superadmin": True,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.info(f"SuperAdmin login successful: {admin.email}")

    return SuperAdminTokenResponse(
        access_token=access_token,
        token_type="bearer",
        admin=SuperAdminResponse.model_validate(admin),
    )


@router.get("/me", response_model=SuperAdminResponse, summary="Get Current SuperAdmin")
async def get_superadmin_me(
    current_admin: SuperAdmin = Depends(get_current_superadmin),
):
    return SuperAdminResponse.model_validate(current_admin)


# ─── Stats Dashboard ──────────────────────────────────────────────────────────

@router.get("/stats", response_model=PlatformStatsResponse, summary="Platform Statistics")
async def get_platform_stats(
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    """Overview of the entire platform."""
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    active_companies = db.query(func.count(Company.id)).filter(Company.is_active == True).scalar() or 0
    inactive_companies = total_companies - active_companies

    total_subs = db.query(func.count(CompanySubscription.id)).scalar() or 0
    active_subs = db.query(func.count(CompanySubscription.id)).filter(
        CompanySubscription.status == SubscriptionStatus.ACTIVE
    ).scalar() or 0
    trial_subs = db.query(func.count(CompanySubscription.id)).filter(
        CompanySubscription.status == SubscriptionStatus.TRIAL
    ).scalar() or 0
    expired_subs = db.query(func.count(CompanySubscription.id)).filter(
        CompanySubscription.status == SubscriptionStatus.EXPIRED
    ).scalar() or 0
    cancelled_subs = db.query(func.count(CompanySubscription.id)).filter(
        CompanySubscription.status == SubscriptionStatus.CANCELLED
    ).scalar() or 0

    total_employees = db.query(func.count(Employee.id)).filter(
        Employee.is_active == True,
        Employee.deleted_at.is_(None),
    ).scalar() or 0

    # Estimate monthly revenue from active subscriptions
    active_sub_records = db.query(CompanySubscription).filter(
        CompanySubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).all()
    total_revenue = sum(
        Decimal(s.billable_seats) * s.price_per_user for s in active_sub_records
    )

    plans = db.query(SubscriptionPlan).all()
    plan_stats = []
    for plan in plans:
        count = db.query(func.count(CompanySubscription.id)).filter(
            CompanySubscription.plan_id == plan.id,
            CompanySubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
        ).scalar() or 0
        plan_stats.append({
            "id": str(plan.id),
            "name": plan.name,
            "plan_key": plan.plan_key,
            "active_subscriptions": count,
            "is_active": plan.is_active,
        })

    return PlatformStatsResponse(
        total_companies=total_companies,
        active_companies=active_companies,
        inactive_companies=inactive_companies,
        total_subscriptions=total_subs,
        active_subscriptions=active_subs,
        trial_subscriptions=trial_subs,
        expired_subscriptions=expired_subs,
        cancelled_subscriptions=cancelled_subs,
        total_employees=total_employees,
        total_revenue_monthly=total_revenue,
        plans=plan_stats,
    )


# ─── Company Management ───────────────────────────────────────────────────────

@router.get("/companies", response_model=List[CompanyBriefResponse], summary="List All Companies")
async def list_companies(
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None, description="Search by company name or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    query = db.query(Company)
    if search:
        query = query.filter(
            (Company.company_name.ilike(f"%{search}%")) | (Company.email.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.filter(Company.is_active == is_active)

    companies = query.order_by(Company.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for company in companies:
        sub = db.query(CompanySubscription).filter(
            CompanySubscription.company_id == company.id
        ).order_by(CompanySubscription.created_at.desc()).first()

        result.append(CompanyBriefResponse(
            id=company.id,
            company_code=company.company_code,
            company_name=company.company_name,
            email=company.email,
            phone=company.phone,
            company_type=str(company.company_type),
            is_active=company.is_active,
            created_at=company.created_at,
            subscription_status=sub.status.value if sub else None,
            subscription_plan=sub.plan.name if sub and sub.plan else None,
            subscription_end=sub.current_period_end if sub else None,
        ))

    return result


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse, summary="Get Company Details")
async def get_company_detail(
    company_id: int,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    total_users = db.query(func.count(User.id)).filter(User.company_id == company_id).scalar() or 0
    total_employees = db.query(func.count(Employee.id)).filter(
        Employee.company_id == company_id,
        Employee.is_active == True,
        Employee.deleted_at.is_(None),
    ).scalar() or 0

    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan)
    ).filter(CompanySubscription.company_id == company_id).first()

    sub_detail = None
    if sub:
        sub_detail = _build_subscription_detail(db, sub)

    return CompanyDetailResponse(
        id=company.id,
        company_code=company.company_code,
        company_name=company.company_name,
        email=company.email,
        phone=company.phone,
        address=company.address,
        company_type=str(company.company_type),
        gst_number=company.gst_number,
        pan_number=company.pan_number,
        is_active=company.is_active,
        created_at=company.created_at,
        updated_at=company.updated_at,
        total_users=total_users,
        total_employees=total_employees,
        subscription=sub_detail,
    )


@router.delete("/companies/{company_id}", response_model=MessageResponse, summary="Delete Company")
async def delete_company(
    company_id: int,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    """
    Permanently delete a company and ALL related data including:
    - All employees and their user accounts
    - All departments, projects, tasks
    - All attendance, leave requests and leave balances
    - All meetings, events
    - All chat messages
    - Subscription, AI usage records
    - Vector store embeddings
    - All uploaded files (profile photos, documents)

    This action is irreversible. Confirm before calling.
    """
    import shutil
    from pathlib import Path
    from app.core.config import settings

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_name = company.company_name

    # ── Step 1: Delete uploaded files from disk ────────────────────────────
    # All files for this company live under UPLOAD_DIR/company_{id}/
    try:
        upload_dir = Path(settings.UPLOAD_DIR) / f"company_{company_id}"
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            logger.info(f"Deleted upload directory: {upload_dir}")
    except Exception as e:
        # Log but don't abort — DB deletion is more important
        logger.error(f"Failed to delete upload directory for company {company_id}: {e}")

    # ── Step 2: Delete the company record ──────────────────────────────────
    # DB cascade (ondelete="CASCADE") handles all child tables automatically:
    # users, employees, departments, projects, tasks, attendance,
    # leave_types, leave_requests, leave_balances,
    # meetings, events, chat_messages,
    # subscriptions, ai_usage, company_ai_usage,
    # vector_store, employee_attachments, department_access
    db.delete(company)
    db.commit()

    logger.info(f"SuperAdmin permanently deleted company: {company_name} (ID: {company_id})")
    return MessageResponse(message=f"Company '{company_name}' and all related data permanently deleted.")


@router.patch("/companies/{company_id}", response_model=MessageResponse, summary="Update Company")
async def update_company(
    company_id: int,
    data: CompanyUpdateRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if data.company_name is not None:
        company.company_name = data.company_name
    if data.phone is not None:
        company.phone = data.phone
    if data.address is not None:
        company.address = data.address
    if data.is_active is not None:
        company.is_active = data.is_active

    company.updated_at = datetime.utcnow()
    db.commit()

    action = "updated"
    if data.is_active is not None:
        action = "activated" if data.is_active else "deactivated"

    logger.info(f"SuperAdmin {action} company {company_id}")
    return MessageResponse(message=f"Company {action} successfully")


# ─── Subscription Management ──────────────────────────────────────────────────

@router.get("/subscriptions", response_model=List[SubscriptionDetailResponse], summary="List All Subscriptions")
async def list_subscriptions(
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    plan_key: Optional[str] = Query(None, description="Filter by plan key"),
):
    query = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    )
    if status_filter:
        try:
            s = SubscriptionStatus(status_filter)
            query = query.filter(CompanySubscription.status == s)
        except ValueError:
            pass
    if plan_key:
        query = query.join(SubscriptionPlan).filter(SubscriptionPlan.plan_key == plan_key)

    subs = query.order_by(CompanySubscription.created_at.desc()).offset(skip).limit(limit).all()
    return [SubscriptionDetailResponse(**_build_subscription_detail(db, s)) for s in subs]


@router.get("/subscriptions/{company_id}", response_model=SubscriptionDetailResponse, summary="Get Company Subscription")
async def get_company_subscription(
    company_id: int,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.company_id == company_id).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.post("/subscriptions/{company_id}", response_model=SubscriptionDetailResponse, status_code=201, summary="Create Subscription for Company")
async def create_subscription_for_company(
    company_id: int,
    data: CreateSubscriptionRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    existing = db.query(CompanySubscription).filter(
        CompanySubscription.company_id == company_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company already has a subscription. Use PATCH to modify it.")

    try:
        plan_uuid = uuid.UUID(data.plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    billing_cycle = BillingCycle(data.billing_cycle.value)
    billable_seats = max(data.seat_count, plan.minimum_seats)
    price_per_user = plan.price_per_user_monthly if billing_cycle == BillingCycle.MONTHLY else plan.price_per_user_yearly

    now = datetime.utcnow()
    period_start = data.current_period_start or now
    if data.current_period_end:
        period_end = data.current_period_end
    else:
        period_end = period_start + (timedelta(days=30) if billing_cycle == BillingCycle.MONTHLY else timedelta(days=365))

    sub = CompanySubscription(
        company_id=company_id,
        plan_id=plan.id,
        billing_cycle=billing_cycle,
        seat_count=data.seat_count,
        billable_seats=billable_seats,
        price_per_user=price_per_user,
        status=SubscriptionStatus(data.status.value),
        current_period_start=period_start,
        current_period_end=period_end,
        trial_end=data.trial_end,
        cancel_at_period_end=False,
    )
    db.add(sub)
    db.flush()

    usage = db.query(SubscriptionUsage).filter(SubscriptionUsage.company_id == company_id).first()
    if not usage:
        usage = SubscriptionUsage(
            company_id=company_id,
            subscription_id=sub.id,
            employees_used=0,
            billable_seats=billable_seats,
        )
        db.add(usage)
    else:
        usage.subscription_id = sub.id
        usage.billable_seats = billable_seats

    now_dt = datetime.now()
    ai_usage = db.query(CompanyAIUsage).filter(
        and_(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.year == now_dt.year,
            CompanyAIUsage.month == now_dt.month,
        )
    ).first()
    if not ai_usage:
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
        ai_usage.queries_limit = plan.ai_queries_limit

    db.commit()
    db.refresh(sub)

    # Reload with relationships
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.id == sub.id).first()

    logger.info(f"SuperAdmin created subscription for company {company_id}")
    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.patch("/subscriptions/{company_id}/extend", response_model=SubscriptionDetailResponse, summary="Extend Subscription Date")
async def extend_subscription(
    company_id: int,
    data: ExtendSubscriptionRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    """
    Extend or set the subscription end date.
    Provide either `days` (adds to current end date) or `new_end_date` (sets absolute date).
    """
    if data.days is None and data.new_end_date is None:
        raise HTTPException(status_code=400, detail="Provide either 'days' or 'new_end_date'")

    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.company_id == company_id).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    if data.new_end_date:
        sub.current_period_end = data.new_end_date
    else:
        current_end = sub.current_period_end or datetime.utcnow()
        # Strip timezone info for arithmetic if present
        if current_end.tzinfo:
            current_end = current_end.replace(tzinfo=None)
        sub.current_period_end = current_end + timedelta(days=data.days)

    # Reactivate if expired
    if sub.status == SubscriptionStatus.EXPIRED:
        sub.status = SubscriptionStatus.ACTIVE

    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)

    logger.info(f"SuperAdmin extended subscription for company {company_id} until {sub.current_period_end}")
    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.patch("/subscriptions/{company_id}/change-plan", response_model=SubscriptionDetailResponse, summary="Change Subscription Plan")
async def change_subscription_plan(
    company_id: int,
    data: ChangePlanRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.company_id == company_id).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    try:
        plan_uuid = uuid.UUID(data.plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    billing_cycle = BillingCycle(data.billing_cycle.value)
    price_per_user = plan.price_per_user_monthly if billing_cycle == BillingCycle.MONTHLY else plan.price_per_user_yearly
    billable_seats = max(sub.seat_count, plan.minimum_seats)

    sub.plan_id = plan.id
    sub.billing_cycle = billing_cycle
    sub.price_per_user = price_per_user
    sub.billable_seats = billable_seats

    if data.reset_period:
        now = datetime.utcnow()
        sub.current_period_start = now
        sub.current_period_end = now + (timedelta(days=30) if billing_cycle == BillingCycle.MONTHLY else timedelta(days=365))

    sub.updated_at = datetime.utcnow()

    # Update AI limit for current month
    now_dt = datetime.now()
    ai_usage = db.query(CompanyAIUsage).filter(
        and_(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.year == now_dt.year,
            CompanyAIUsage.month == now_dt.month,
        )
    ).first()
    if ai_usage:
        ai_usage.queries_limit = plan.ai_queries_limit

    db.commit()
    db.refresh(sub)

    # Reload with relationships
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.id == sub.id).first()

    logger.info(f"SuperAdmin changed plan for company {company_id} to {plan.name}")
    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.patch("/subscriptions/{company_id}/change-status", response_model=SubscriptionDetailResponse, summary="Change Subscription Status")
async def change_subscription_status(
    company_id: int,
    data: ChangeStatusRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.company_id == company_id).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    new_status = SubscriptionStatus(data.status.value)
    sub.status = new_status

    if new_status == SubscriptionStatus.CANCELLED:
        sub.cancelled_at = datetime.utcnow()
        sub.cancel_at_period_end = False
    elif new_status == SubscriptionStatus.ACTIVE:
        sub.cancelled_at = None
        sub.cancel_at_period_end = False

    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)

    logger.info(f"SuperAdmin changed subscription status for company {company_id} to {new_status.value}")
    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.patch("/subscriptions/{company_id}/update-seats", response_model=SubscriptionDetailResponse, summary="Update Subscription Seats")
async def update_subscription_seats(
    company_id: int,
    data: UpdateSeatsRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.company_id == company_id).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    sub.seat_count = data.seat_count
    if data.billable_seats is not None:
        sub.billable_seats = data.billable_seats
    else:
        sub.billable_seats = max(data.seat_count, sub.plan.minimum_seats if sub.plan else 1)

    usage = db.query(SubscriptionUsage).filter(SubscriptionUsage.company_id == company_id).first()
    if usage:
        usage.billable_seats = sub.billable_seats
        usage.updated_at = datetime.utcnow()

    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)

    logger.info(f"SuperAdmin updated seats for company {company_id}: {sub.billable_seats}")
    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.patch("/subscriptions/{company_id}/update-ai-limit", response_model=SubscriptionDetailResponse, summary="Update AI Query Limit")
async def update_ai_limit(
    company_id: int,
    data: UpdateAILimitRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    sub = db.query(CompanySubscription).options(
        joinedload(CompanySubscription.plan),
        joinedload(CompanySubscription.company),
    ).filter(CompanySubscription.company_id == company_id).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    now_dt = datetime.now()
    ai_usage = db.query(CompanyAIUsage).filter(
        and_(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.year == now_dt.year,
            CompanyAIUsage.month == now_dt.month,
        )
    ).first()

    if not ai_usage:
        ai_usage = CompanyAIUsage(
            company_id=company_id,
            year=now_dt.year,
            month=now_dt.month,
            queries_used=0,
            queries_limit=data.queries_limit,
            extra_queries_purchased=data.extra_queries or 0,
        )
        db.add(ai_usage)
    else:
        ai_usage.queries_limit = data.queries_limit
        if data.extra_queries is not None:
            ai_usage.extra_queries_purchased = data.extra_queries
        ai_usage.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"SuperAdmin updated AI limit for company {company_id}: {data.queries_limit}")
    return SubscriptionDetailResponse(**_build_subscription_detail(db, sub))


@router.delete("/subscriptions/{company_id}", response_model=MessageResponse, summary="Delete Subscription")
async def delete_subscription(
    company_id: int,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    sub = db.query(CompanySubscription).filter(CompanySubscription.company_id == company_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this company")

    db.delete(sub)
    db.commit()

    logger.info(f"SuperAdmin deleted subscription for company {company_id}")
    return MessageResponse(message="Subscription deleted successfully")


# ─── Plan Management ──────────────────────────────────────────────────────────


@router.get(
    "/plans/modules-catalog",
    response_model=PlanModulesCatalogResponse,
    summary="Product modules catalog for plans",
)
async def get_plan_modules_catalog(
    _: SuperAdmin = Depends(get_current_superadmin),
    ai_queries_limit: Optional[int] = Query(
        None,
        ge=0,
        description="Optional: include a suggested price floor for this monthly AI query cap",
    ),
):
    """
    Lists **only modules that exist in this backend** (for plan feature toggles).

    Includes a simple **margin vs AI usage** floor for pricing. Tune cost assumptions
    in `app/api/v1/constants/product_modules.py` from your real OpenAI bills.
    """
    pb = pricing_playbook_text()
    floor = None
    if ai_queries_limit is not None:
        floor = estimate_pricing_floor(ai_queries_limit=ai_queries_limit)

    return PlanModulesCatalogResponse(
        modules=[ProductModuleItem(**m) for m in PRODUCT_MODULES],
        feature_keys=sorted(MODULE_KEYS),
        default_features=default_features_all_false(),
        pricing_playbook=PricingPlaybookResponse(
            currency=pb["currency"],
            assumptions=pb["assumptions"],
            margin_target_percent=pb["margin_target_percent"],
            sales_notes=pb["sales_notes"],
        ),
        pricing_floor_for_ai_limit=floor,
    )


@router.get("/plans", response_model=List[PlanResponse], summary="List All Plans")
async def list_plans(
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
    include_inactive: bool = Query(False),
):
    query = db.query(SubscriptionPlan)
    if not include_inactive:
        query = query.filter(SubscriptionPlan.is_active == True)
    plans = query.order_by(SubscriptionPlan.price_per_user_monthly).all()
    return [
        PlanResponse(
            id=str(p.id),
            name=p.name,
            plan_key=p.plan_key,
            price_per_user_monthly=p.price_per_user_monthly,
            price_per_user_yearly=p.price_per_user_yearly,
            minimum_seats=p.minimum_seats,
            ai_queries_limit=p.ai_queries_limit,
            features=p.features,
            is_active=p.is_active,
            created_at=p.created_at,
        )
        for p in plans
    ]


@router.post("/plans", response_model=PlanResponse, status_code=201, summary="Create Subscription Plan")
async def create_plan(
    data: PlanCreateRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    existing = db.query(SubscriptionPlan).filter(
        (SubscriptionPlan.name == data.name) | (SubscriptionPlan.plan_key == data.plan_key)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plan with this name or key already exists")

    unknown = list_unknown_feature_keys(data.features)
    if unknown:
        logger.warning("Create plan: dropping unknown feature keys (not in product catalog): %s", unknown)
    features_clean = sanitize_plan_features(data.features)

    plan = SubscriptionPlan(
        name=data.name,
        plan_key=data.plan_key,
        price_per_user_monthly=data.price_per_user_monthly,
        price_per_user_yearly=data.price_per_user_yearly,
        minimum_seats=data.minimum_seats,
        ai_queries_limit=data.ai_queries_limit,
        features=features_clean,
        is_active=data.is_active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    logger.info(f"SuperAdmin created plan: {plan.name}")
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        plan_key=plan.plan_key,
        price_per_user_monthly=plan.price_per_user_monthly,
        price_per_user_yearly=plan.price_per_user_yearly,
        minimum_seats=plan.minimum_seats,
        ai_queries_limit=plan.ai_queries_limit,
        features=plan.features,
        is_active=plan.is_active,
        created_at=plan.created_at,
    )


@router.patch("/plans/{plan_id}", response_model=PlanResponse, summary="Update Subscription Plan")
async def update_plan(
    plan_id: str,
    data: PlanUpdateRequest,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    try:
        plan_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if data.name is not None:
        plan.name = data.name
    if data.price_per_user_monthly is not None:
        plan.price_per_user_monthly = data.price_per_user_monthly
    if data.price_per_user_yearly is not None:
        plan.price_per_user_yearly = data.price_per_user_yearly
    if data.minimum_seats is not None:
        plan.minimum_seats = data.minimum_seats
    if data.ai_queries_limit is not None:
        plan.ai_queries_limit = data.ai_queries_limit
    if data.features is not None:
        unknown = list_unknown_feature_keys(data.features)
        if unknown:
            logger.warning("Update plan: dropping unknown feature keys: %s", unknown)
        plan.features = sanitize_plan_features(data.features)
    if data.is_active is not None:
        plan.is_active = data.is_active

    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)

    logger.info(f"SuperAdmin updated plan: {plan.name}")
    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        plan_key=plan.plan_key,
        price_per_user_monthly=plan.price_per_user_monthly,
        price_per_user_yearly=plan.price_per_user_yearly,
        minimum_seats=plan.minimum_seats,
        ai_queries_limit=plan.ai_queries_limit,
        features=plan.features,
        is_active=plan.is_active,
        created_at=plan.created_at,
    )


@router.delete("/plans/{plan_id}", response_model=MessageResponse, summary="Delete Subscription Plan")
async def delete_plan(
    plan_id: str,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
):
    try:
        plan_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check if any active subscriptions use this plan
    active_count = db.query(func.count(CompanySubscription.id)).filter(
        CompanySubscription.plan_id == plan_uuid,
        CompanySubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
    ).scalar() or 0

    if active_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete plan with {active_count} active subscription(s). Deactivate it instead."
        )

    db.delete(plan)
    db.commit()

    logger.info(f"SuperAdmin deleted plan: {plan_id}")
    return MessageResponse(message="Plan deleted successfully")


# ─── AI Usage Tracking ────────────────────────────────────────────────────────

@router.get("/ai-usage", summary="Platform-wide AI Usage Overview")
async def get_platform_ai_usage(
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month 1-12 (default: current month)"),
):
    """
    Platform-wide AI usage summary across all companies for a given month.
    Shows each company's query count, token consumption, and limit utilisation.
    Sorted by highest token usage.
    """
    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month

    # Per-company token & query totals from ai_usage detail table
    rows = db.query(
        AIUsage.company_id,
        func.count(AIUsage.id).label("total_queries"),
        func.sum(AIUsage.tokens_used).label("total_tokens"),
        func.max(AIUsage.created_at).label("last_used"),
    ).filter(
        func.extract("year", AIUsage.created_at) == target_year,
        func.extract("month", AIUsage.created_at) == target_month,
    ).group_by(AIUsage.company_id).all()

    # Build company id → name map
    from app.api.v1.models.company_model import Company
    company_ids = [r.company_id for r in rows]
    companies_map = {
        c.id: c.company_name
        for c in db.query(Company).filter(Company.id.in_(company_ids)).all()
    }

    # Pull monthly usage records for limit info
    monthly_map = {
        u.company_id: u
        for u in db.query(CompanyAIUsage).filter(
            CompanyAIUsage.year == target_year,
            CompanyAIUsage.month == target_month,
            CompanyAIUsage.company_id.in_(company_ids),
        ).all()
    }

    company_stats = []
    for r in sorted(rows, key=lambda x: -(x.total_tokens or 0)):
        monthly = monthly_map.get(r.company_id)
        queries_limit = monthly.total_limit if monthly else 0
        queries_used = monthly.queries_used if monthly else r.total_queries
        company_stats.append({
            "company_id": r.company_id,
            "company_name": companies_map.get(r.company_id, "Unknown"),
            "total_queries": r.total_queries,
            "total_tokens": int(r.total_tokens or 0),
            "queries_limit": queries_limit,
            "queries_used": queries_used,
            "queries_remaining": max(0, queries_limit - queries_used),
            "utilisation_pct": round((queries_used / queries_limit * 100), 1) if queries_limit else 0,
            "last_used": r.last_used.isoformat() if r.last_used else None,
        })

    return {
        "period": f"{target_year}-{target_month:02d}",
        "total_companies_active": len(company_stats),
        "platform_total_queries": sum(c["total_queries"] for c in company_stats),
        "platform_total_tokens": sum(c["total_tokens"] for c in company_stats),
        "companies": company_stats,
    }


@router.get("/ai-usage/{company_id}", summary="Company AI Usage — Per User Breakdown")
async def get_company_ai_usage_detail(
    company_id: int,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month 1-12 (default: current month)"),
):
    """
    Detailed AI usage for a single company broken down by user.
    SuperAdmin can see exactly which employee or admin consumed how many tokens.
    """
    from app.api.v1.models.company_model import Company

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month

    # Per-user totals
    rows = db.query(
        AIUsage.user_id,
        func.count(AIUsage.id).label("total_queries"),
        func.sum(AIUsage.tokens_used).label("total_tokens"),
        func.max(AIUsage.created_at).label("last_used"),
    ).filter(
        AIUsage.company_id == company_id,
        func.extract("year", AIUsage.created_at) == target_year,
        func.extract("month", AIUsage.created_at) == target_month,
    ).group_by(AIUsage.user_id).all()

    user_ids = [r.user_id for r in rows if r.user_id]
    users_map = {
        u.id: {"name": u.full_name, "email": u.email, "role": u.role.value}
        for u in db.query(UserModel).filter(
            UserModel.company_id == company_id,
            UserModel.id.in_(user_ids),
        ).all()
    }

    # Monthly company-level record
    monthly = db.query(CompanyAIUsage).filter(
        CompanyAIUsage.company_id == company_id,
        CompanyAIUsage.year == target_year,
        CompanyAIUsage.month == target_month,
    ).first()

    user_stats = []
    for r in sorted(rows, key=lambda x: -(x.total_tokens or 0)):
        info = users_map.get(r.user_id, {"name": "Unknown", "email": "", "role": "unknown"})
        user_stats.append({
            "user_id": r.user_id,
            "user_name": info["name"],
            "email": info["email"],
            "role": info["role"],
            "total_queries": r.total_queries,
            "total_tokens": int(r.total_tokens or 0),
            "last_used": r.last_used.isoformat() if r.last_used else None,
        })

    return {
        "company_id": company_id,
        "company_name": company.company_name,
        "period": f"{target_year}-{target_month:02d}",
        "queries_used": monthly.queries_used if monthly else 0,
        "queries_limit": monthly.total_limit if monthly else 0,
        "queries_remaining": monthly.remaining_queries if monthly else 0,
        "total_tokens_this_month": sum(u["total_tokens"] for u in user_stats),
        "users": user_stats,
    }


@router.get("/ai-usage/{company_id}/history", summary="Company AI Usage — Monthly History")
async def get_company_ai_usage_history(
    company_id: int,
    _: SuperAdmin = Depends(get_current_superadmin),
    db: Session = Depends(get_database_session),
    months: int = Query(6, ge=1, le=24, description="Number of past months to include"),
):
    """
    Month-by-month AI usage history for a single company.
    Useful for spotting usage trends or sudden spikes.
    """
    from app.api.v1.models.company_model import Company

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    now = datetime.utcnow()
    periods = []
    y, m = now.year, now.month
    for _ in range(months):
        periods.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    history = []
    for y, m in reversed(periods):
        monthly = db.query(CompanyAIUsage).filter(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.year == y,
            CompanyAIUsage.month == m,
        ).first()

        token_total = db.query(func.sum(AIUsage.tokens_used)).filter(
            AIUsage.company_id == company_id,
            func.extract("year", AIUsage.created_at) == y,
            func.extract("month", AIUsage.created_at) == m,
        ).scalar() or 0

        unique_users = db.query(func.count(func.distinct(AIUsage.user_id))).filter(
            AIUsage.company_id == company_id,
            func.extract("year", AIUsage.created_at) == y,
            func.extract("month", AIUsage.created_at) == m,
        ).scalar() or 0

        history.append({
            "period": f"{y}-{m:02d}",
            "year": y,
            "month": m,
            "queries_used": monthly.queries_used if monthly else 0,
            "queries_limit": monthly.total_limit if monthly else 0,
            "tokens_used": int(token_total),
            "active_users": unique_users,
        })

    return {
        "company_id": company_id,
        "company_name": company.company_name,
        "months_included": months,
        "history": history,
    }
