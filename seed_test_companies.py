"""
Seed script — creates test companies for Restaurant, Temple, and Hospital
with admin logins, employees, departments, subscription (all modules), and
industry-specific sample data (inventory, shifts, bookings, donations).

Run: python seed_test_companies.py
Safe to re-run — skips companies that already exist (checks by email).

LOGIN CREDENTIALS (printed at the end and saved to test_credentials.txt)
"""
import sys
import logging
from datetime import date, datetime, time
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── Test company definitions ──────────────────────────────────────────────────

COMPANIES = [
    {
        "industry": "restaurant",
        "company_name": "Spice Garden Restaurant",
        "company_email": "admin@spicegarden.test",
        "admin_username": "spicegarden_admin",
        "admin_email": "admin@spicegarden.test",
        "admin_full_name": "Ravi Kumar",
        "password": "SpiceGarden@123",
        "phone": "9876543210",
        "address": "12, MG Road, Bangalore",
        "pan_number": "ABCDE1234F",
        "departments": ["Kitchen", "Service Floor", "Management", "Delivery"],
        "employees": [
            {"first_name": "Anand",  "last_name": "Chef",     "position": "Head Chef",       "dept": "Kitchen"},
            {"first_name": "Priya",  "last_name": "Sharma",   "position": "Sous Chef",       "dept": "Kitchen"},
            {"first_name": "Kiran",  "last_name": "Waiter",   "position": "Waiter",          "dept": "Service Floor"},
            {"first_name": "Meena",  "last_name": "Cashier",  "position": "Cashier",         "dept": "Management"},
        ],
        "shifts": [
            {"name": "Morning Shift",   "start": "08:00", "end": "16:00"},
            {"name": "Evening Shift",   "start": "16:00", "end": "00:00"},
            {"name": "Night Shift",     "start": "00:00", "end": "08:00"},
        ],
        "inventory": [
            {"name": "Basmati Rice",     "unit": "kg",      "qty": 50,  "reorder": 10, "price": 80},
            {"name": "Tomatoes",         "unit": "kg",      "qty": 20,  "reorder": 5,  "price": 25},
            {"name": "Chicken",          "unit": "kg",      "qty": 30,  "reorder": 10, "price": 180},
            {"name": "Cooking Oil",      "unit": "liters",  "qty": 15,  "reorder": 5,  "price": 150},
            {"name": "Onions",           "unit": "kg",      "qty": 25,  "reorder": 8,  "price": 20},
            {"name": "Paneer",           "unit": "kg",      "qty": 8,   "reorder": 3,  "price": 300},
            {"name": "Gas Cylinder",     "unit": "units",   "qty": 4,   "reorder": 2,  "price": 900},
            {"name": "Paper Plates",     "unit": "packets", "qty": 30,  "reorder": 10, "price": 60},
        ],
        "booking_resources": [
            {"name": "Table 1 (2-seater)",  "type": "table", "capacity": 2},
            {"name": "Table 2 (4-seater)",  "type": "table", "capacity": 4},
            {"name": "Table 3 (6-seater)",  "type": "table", "capacity": 6},
            {"name": "Private Dining Room", "type": "room",  "capacity": 20},
        ],
        "clients": [
            {"name": "Rahul Mehta",    "phone": "9111111111", "label": "customer"},
            {"name": "Sunita Patel",   "phone": "9222222222", "label": "customer"},
            {"name": "City Corp Ltd",  "phone": "9333333333", "label": "corporate_client"},
        ],
    },
    {
        "industry": "temple",
        "company_name": "Sri Venkateswara Temple Trust",
        "company_email": "admin@svtemple.test",
        "admin_username": "svtemple_admin",
        "admin_email": "admin@svtemple.test",
        "admin_full_name": "Sharma Dikshitar",
        "password": "Temple@123",
        "phone": "9876500001",
        "address": "Temple Road, Tirupati",
        "pan_number": "SVTMP1234T",
        "departments": ["Pujaris", "Administration", "Annadanam", "Security", "Maintenance"],
        "employees": [
            {"first_name": "Venkata",  "last_name": "Priest",   "position": "Head Pujari",         "dept": "Pujaris"},
            {"first_name": "Ramaiah",  "last_name": "Archaka",  "position": "Archaka",             "dept": "Pujaris"},
            {"first_name": "Lakshmi",  "last_name": "Devi",     "position": "Annadanam Manager",   "dept": "Annadanam"},
            {"first_name": "Suresh",   "last_name": "Security", "position": "Security Guard",      "dept": "Security"},
        ],
        "shifts": [
            {"name": "Morning Pooja",    "start": "05:00", "end": "13:00"},
            {"name": "Afternoon Pooja",  "start": "13:00", "end": "21:00"},
            {"name": "Night Shift",      "start": "21:00", "end": "05:00"},
        ],
        "inventory": [
            {"name": "Flowers (Lotus)",    "unit": "kg",      "qty": 10,  "reorder": 3,  "price": 200},
            {"name": "Coconuts",           "unit": "pieces",  "qty": 200, "reorder": 50, "price": 15},
            {"name": "Camphor",            "unit": "grams",   "qty": 500, "reorder": 100,"price": 5},
            {"name": "Incense Sticks",     "unit": "packets", "qty": 50,  "reorder": 10, "price": 20},
            {"name": "Prasad Rice",        "unit": "kg",      "qty": 100, "reorder": 30, "price": 55},
            {"name": "Ghee",               "unit": "kg",      "qty": 20,  "reorder": 5,  "price": 500},
            {"name": "Turmeric Powder",    "unit": "kg",      "qty": 5,   "reorder": 2,  "price": 80},
            {"name": "Sandal Paste",       "unit": "grams",   "qty": 300, "reorder": 100,"price": 10},
        ],
        "booking_resources": [
            {"name": "Main Sanctum Slot",     "type": "pooja_slot", "capacity": 10},
            {"name": "Kalyana Mandapam",      "type": "venue",      "capacity": 200},
            {"name": "Annadanam Hall",        "type": "venue",      "capacity": 500},
            {"name": "Special Darshan Slot",  "type": "darshan_slot","capacity": 50},
        ],
        "clients": [
            {"name": "Rajaram Iyer",      "phone": "9444444444", "label": "devotee"},
            {"name": "Padmavathi Devi",   "phone": "9555555555", "label": "devotee"},
            {"name": "Srinivasa Trust",   "phone": "9666666666", "label": "donor_organization"},
        ],
        "donations": [
            {"donor": "Rajaram Iyer",    "amount": 5000,  "purpose": "Temple Renovation",  "mode": "online"},
            {"donor": "Anonymous",       "amount": 1000,  "purpose": "Annadanam",           "mode": "cash"},
            {"donor": "Padmavathi Devi", "amount": 2500,  "purpose": "Gopuram Maintenance", "mode": "upi"},
        ],
    },
    {
        "industry": "hospital",
        "company_name": "CareFirst Multi-Specialty Hospital",
        "company_email": "admin@carefirst.test",
        "admin_username": "carefirst_admin",
        "admin_email": "admin@carefirst.test",
        "admin_full_name": "Dr. Anitha Reddy",
        "password": "Hospital@123",
        "phone": "9876500002",
        "address": "45, Health City, Hyderabad",
        "pan_number": "CFRST1234H",
        "departments": ["General Medicine", "Surgery", "Nursing", "Pharmacy", "Reception", "Radiology"],
        "employees": [
            {"first_name": "Dr. Vikram", "last_name": "Rao",     "position": "Senior Doctor",       "dept": "General Medicine"},
            {"first_name": "Dr. Seema",  "last_name": "Nair",    "position": "Surgeon",             "dept": "Surgery"},
            {"first_name": "Kavya",      "last_name": "Nurse",   "position": "Head Nurse",          "dept": "Nursing"},
            {"first_name": "Arun",       "last_name": "Pharma",  "position": "Pharmacist",          "dept": "Pharmacy"},
            {"first_name": "Deepa",      "last_name": "Recep",   "position": "Receptionist",        "dept": "Reception"},
        ],
        "shifts": [
            {"name": "Morning Shift",   "start": "07:00", "end": "15:00"},
            {"name": "Evening Shift",   "start": "15:00", "end": "23:00"},
            {"name": "Night Shift",     "start": "23:00", "end": "07:00"},
        ],
        "inventory": [
            {"name": "Paracetamol 500mg",   "unit": "tablets",  "qty": 1000, "reorder": 200, "price": 1},
            {"name": "Amoxicillin 250mg",   "unit": "capsules", "qty": 500,  "reorder": 100, "price": 5},
            {"name": "IV Saline 500ml",     "unit": "bottles",  "qty": 100,  "reorder": 30,  "price": 45},
            {"name": "Surgical Gloves",     "unit": "pairs",    "qty": 500,  "reorder": 100, "price": 8},
            {"name": "Syringes 5ml",        "unit": "pieces",   "qty": 1000, "reorder": 200, "price": 3},
            {"name": "Bandages",            "unit": "rolls",    "qty": 200,  "reorder": 50,  "price": 25},
            {"name": "Antiseptic Solution", "unit": "liters",   "qty": 20,   "reorder": 5,   "price": 120},
            {"name": "Blood Glucose Strips","unit": "boxes",    "qty": 50,   "reorder": 10,  "price": 350},
        ],
        "booking_resources": [
            {"name": "OPD Room 1 - General",    "type": "doctor_slot", "capacity": 1},
            {"name": "OPD Room 2 - Surgeon",    "type": "doctor_slot", "capacity": 1},
            {"name": "Operation Theatre 1",     "type": "ot",          "capacity": 5},
            {"name": "ICU Bed",                 "type": "bed",         "capacity": 10},
            {"name": "X-Ray Room",              "type": "diagnostic",  "capacity": 1},
        ],
        "clients": [
            {"name": "Suresh Kumar",    "phone": "9777777777", "label": "patient",
             "attrs": {"blood_group": "O+", "age": 45, "allergies": "Penicillin"}},
            {"name": "Meena Sharma",    "phone": "9888888888", "label": "patient",
             "attrs": {"blood_group": "A+", "age": 32, "allergies": "None"}},
            {"name": "Raju Pillai",     "phone": "9999999999", "label": "patient",
             "attrs": {"blood_group": "B-", "age": 60, "allergies": "Aspirin"}},
        ],
    },
]

# ─── All modules enabled plan features ────────────────────────────────────────

ALL_MODULES_FEATURES = {
    "employees": True, "departments": True, "tasks": True, "projects": True,
    "attendance": True, "leaves": True, "dashboard": True, "ai_chat": True,
    "chat": True, "meetings": True, "events": True, "calendar": True,
    "subscriptions": True,
    "inventory": True, "assets": True, "crm": True, "booking": True,
    "billing_ops": True, "shifts": True, "donations": True,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(t: str) -> time:
    h, m = t.split(":")
    return time(int(h), int(m))


def _get_or_create_scale_plan(db):
    from app.api.v1.models.subscription_model import SubscriptionPlan
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "scale").first()
    if plan:
        plan.features = ALL_MODULES_FEATURES
        db.commit()
        db.refresh(plan)
    return plan


def _create_company_subscription(db, company_id: int, plan):
    from app.api.v1.models.subscription_model import (
        CompanySubscription, SubscriptionUsage, BillingCycle, SubscriptionStatus
    )
    from datetime import datetime
    existing = db.query(CompanySubscription).filter(
        CompanySubscription.company_id == company_id
    ).first()
    if existing:
        return existing

    sub = CompanySubscription(
        company_id=company_id,
        plan_id=plan.id,
        billing_cycle=BillingCycle.MONTHLY,
        seat_count=20,
        billable_seats=20,
        price_per_user=plan.price_per_user_monthly,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime(2099, 12, 31),
    )
    db.add(sub)
    db.flush()

    usage = SubscriptionUsage(
        company_id=company_id,
        subscription_id=sub.id,
        employees_used=0,
        billable_seats=0,
    )
    db.add(usage)
    db.commit()
    return sub


def _seed_company(db, cfg: dict, plan) -> dict:
    from app.api.v1.models.company_model import Company, CompanyType
    from app.api.v1.models.user_model import User, UserRole
    from app.api.v1.models.department_model import Department
    from app.api.v1.models.employee_model import Employee
    from app.api.v1.models.leave_model import LeaveType
    from app.api.v1.models.company_profile_model import CompanyProfile, IndustryType
    from app.api.v1.models.inventory_model import InventoryCategory, InventoryItem, ItemType
    from app.api.v1.models.shift_model import Shift, ShiftAssignment
    from app.api.v1.models.booking_model import BookingResource
    from app.api.v1.models.crm_model import Client, ClientType
    from app.api.v1.models.donation_model import Donation, DonationMode
    from app.core.security import hash_password_for_storage
    from app.api.v1.services.auth_service import generate_unique_company_code

    # ── 1. Company ─────────────────────────────────────────────────────────────
    existing = db.query(Company).filter(Company.email == cfg["company_email"]).first()
    if existing:
        # Check if it has employees — if not, it's an incomplete seed, delete and redo
        from app.api.v1.models.employee_model import Employee as EmpCheck
        emp_count = db.query(EmpCheck).filter(EmpCheck.company_id == existing.id).count()
        if emp_count > 0:
            logger.info(f"  Company '{cfg['company_name']}' already fully seeded — skipping")
            return {"skipped": True, "company_name": cfg["company_name"]}
        else:
            logger.info(f"  Company '{cfg['company_name']}' exists but is incomplete — deleting and reseeding")
            db.delete(existing)
            db.commit()

    company_code = generate_unique_company_code(db)
    company = Company(
        company_code=company_code,
        company_name=cfg["company_name"],
        email=cfg["company_email"],
        phone=cfg["phone"],
        address=cfg["address"],
        company_type=CompanyType.ORGANIZATION.value,
        pan_number=cfg["pan_number"],
        is_active=True,
    )
    db.add(company)
    db.flush()
    company_id = company.id
    logger.info(f"  Created company: {company.company_name} (ID: {company_id})")

    # ── 2. Admin user ──────────────────────────────────────────────────────────
    hashed_pw = hash_password_for_storage(cfg["password"])
    admin = User(
        company_id=company_id,
        email=cfg["admin_email"],
        username=cfg["admin_username"],
        full_name=cfg["admin_full_name"],
        hashed_password=hashed_pw,
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=False,
        force_password_change=False,
    )
    db.add(admin)
    db.flush()
    logger.info(f"  Created admin: {admin.username}")

    # ── 3. Subscription (all modules, scale plan) ─────────────────────────────
    _create_company_subscription(db, company_id, plan)
    logger.info("  Subscription: Scale plan — all modules enabled")

    # ── 4. Industry profile ────────────────────────────────────────────────────
    industry_map = {
        "restaurant": IndustryType.RESTAURANT,
        "temple": IndustryType.TEMPLE,
        "hospital": IndustryType.HOSPITAL,
    }
    profile = CompanyProfile(
        company_id=company_id,
        industry_type=industry_map[cfg["industry"]],
        enabled_modules={k: True for k in ALL_MODULES_FEATURES},
        custom_roles={
            "restaurant": ["chef", "waiter", "cashier", "kitchen_manager"],
            "temple":     ["priest", "archaka", "trustee", "volunteer"],
            "hospital":   ["doctor", "nurse", "pharmacist", "receptionist", "lab_technician"],
        }[cfg["industry"]],
    )
    db.add(profile)
    db.flush()
    logger.info(f"  Industry profile: {cfg['industry']}")

    # ── 5. Default leave types ─────────────────────────────────────────────────
    leave_types_data = [
        {"name": "Casual Leave",   "code": "CL",  "max_days": 12, "is_paid": True},
        {"name": "Sick Leave",     "code": "SL",  "max_days": 10, "is_paid": True},
        {"name": "Annual Leave",   "code": "AL",  "max_days": 15, "is_paid": True},
        {"name": "Unpaid Leave",   "code": "UL",  "max_days": 30, "is_paid": False},
    ]
    for lt_data in leave_types_data:
        lt = LeaveType(
            company_id=company_id,
            name=lt_data["name"],
            code=lt_data["code"],
            max_days_per_year=lt_data["max_days"],
            is_paid=lt_data["is_paid"],
            is_active=True,
        )
        db.add(lt)
    db.flush()

    # ── 6. Departments ─────────────────────────────────────────────────────────
    dept_map = {}
    for dept_name in cfg["departments"]:
        dept = Department(company_id=company_id, name=dept_name, is_active=True)
        db.add(dept)
        db.flush()
        dept_map[dept_name] = dept.id
    logger.info(f"  Departments: {list(dept_map.keys())}")

    # ── 7. Employees (with login credentials) ─────────────────────────────────
    employee_creds = []
    for i, emp_cfg in enumerate(cfg["employees"]):
        # Use global last employee (employee_code is globally unique, not per-company)
        last_emp = db.query(Employee).order_by(Employee.id.desc()).first()
        if last_emp and last_emp.employee_code and last_emp.employee_code.startswith("EMP"):
            try:
                emp_code = f"EMP{int(last_emp.employee_code[3:]) + 1:08d}"
            except ValueError:
                emp_code = "EMP00000001"
        else:
            emp_code = "EMP00000001"
        emp = Employee(
            company_id=company_id,
            department_id=dept_map.get(emp_cfg["dept"]),
            employee_code=emp_code,
            first_name=emp_cfg["first_name"],
            last_name=emp_cfg["last_name"],
            email=f"{emp_cfg['first_name'].lower().replace(' ', '').replace('.', '')}.{emp_cfg['last_name'].lower()}@{cfg['company_email'].split('@')[1]}",
            position=emp_cfg["position"],
            hire_date=date(2024, 1, 1),
            is_active=True,
        )
        db.add(emp)
        db.flush()

        emp_username = f"{emp_cfg['first_name'].lower().replace(' ', '').replace('.', '')}_{company_id}"
        emp_password = f"Pass@{emp_code}"
        emp_user = User(
            company_id=company_id,
            employee_id=emp.id,
            email=emp.email,
            username=emp_username,
            full_name=f"{emp_cfg['first_name']} {emp_cfg['last_name']}",
            hashed_password=hash_password_for_storage(emp_password),
            role=UserRole.EMPLOYEE,
            is_active=True,
            force_password_change=False,
        )
        db.add(emp_user)
        db.flush()
        employee_creds.append({
            "name": f"{emp_cfg['first_name']} {emp_cfg['last_name']}",
            "position": emp_cfg["position"],
            "username": emp_username,
            "password": emp_password,
            "employee_id": emp.id,
        })
    logger.info(f"  Created {len(employee_creds)} employees")

    # ── 8. Shifts ──────────────────────────────────────────────────────────────
    shift_objs = []
    for sh in cfg.get("shifts", []):
        shift = Shift(
            company_id=company_id,
            name=sh["name"],
            start_time=_parse_time(sh["start"]),
            end_time=_parse_time(sh["end"]),
            shift_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            is_active=True,
        )
        db.add(shift)
        db.flush()
        shift_objs.append(shift)
    if shift_objs:
        logger.info(f"  Created {len(shift_objs)} shifts")

    # ── 9. Inventory ───────────────────────────────────────────────────────────
    if cfg.get("inventory"):
        cat = InventoryCategory(company_id=company_id, name="General", is_active=True)
        db.add(cat)
        db.flush()
        for i, item_cfg in enumerate(cfg["inventory"]):
            sku_prefix = "".join(c.upper() for c in item_cfg["name"][:3] if c.isalpha()) or "ITM"
            item = InventoryItem(
                company_id=company_id,
                category_id=cat.id,
                name=item_cfg["name"],
                sku=f"{sku_prefix}{i + 1:04d}",
                item_type=ItemType.CONSUMABLE,
                unit=item_cfg["unit"],
                quantity_on_hand=Decimal(str(item_cfg["qty"])),
                reorder_level=Decimal(str(item_cfg["reorder"])),
                unit_price=Decimal(str(item_cfg["price"])),
                is_active=True,
            )
            db.add(item)
        logger.info(f"  Created {len(cfg['inventory'])} inventory items")

    # ── 10. Booking resources ──────────────────────────────────────────────────
    if cfg.get("booking_resources"):
        for res_cfg in cfg["booking_resources"]:
            res = BookingResource(
                company_id=company_id,
                name=res_cfg["name"],
                resource_type=res_cfg["type"],
                capacity=res_cfg.get("capacity"),
                is_active=True,
            )
            db.add(res)
        logger.info(f"  Created {len(cfg['booking_resources'])} booking resources")

    # ── 11. CRM clients ────────────────────────────────────────────────────────
    if cfg.get("clients"):
        for cl_cfg in cfg["clients"]:
            client = Client(
                company_id=company_id,
                client_type=ClientType.INDIVIDUAL,
                name=cl_cfg["name"],
                phone=cl_cfg.get("phone"),
                industry_label=cl_cfg.get("label"),
                custom_attributes=cl_cfg.get("attrs"),
                is_active=True,
            )
            db.add(client)
        logger.info(f"  Created {len(cfg['clients'])} CRM clients")

    # ── 12. Donations (temple only) ────────────────────────────────────────────
    if cfg.get("donations"):
        mode_map = {
            "cash": DonationMode.CASH, "online": DonationMode.ONLINE,
            "upi": DonationMode.UPI, "cheque": DonationMode.CHEQUE,
        }
        for i, don_cfg in enumerate(cfg["donations"]):
            receipt = f"RCP-TEST-{i + 1:05d}"
            donation = Donation(
                company_id=company_id,
                donor_name=don_cfg["donor"],
                amount=Decimal(str(don_cfg["amount"])),
                purpose=don_cfg["purpose"],
                donation_mode=mode_map.get(don_cfg["mode"], DonationMode.CASH),
                receipt_number=receipt,
                donated_at=datetime.utcnow(),
                received_by_user_id=admin.id,
            )
            db.add(donation)
        logger.info(f"  Created {len(cfg['donations'])} donation records")

    db.commit()
    logger.info(f"  Committed all data for {cfg['company_name']}")

    return {
        "skipped": False,
        "company_name": cfg["company_name"],
        "company_code": company_code,
        "industry": cfg["industry"],
        "admin_username": cfg["admin_username"],
        "admin_password": cfg["password"],
        "admin_email": cfg["admin_email"],
        "employees": employee_creds,
    }


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    from app.db.base import Base
    from app.db.session import SessionLocal

    # Run business OS migration first
    logger.info("Running Business OS migration (create new tables if missing)...")
    try:
        import subprocess
        result = subprocess.run([sys.executable, "migrate_business_os.py"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Migration OK")
        else:
            logger.warning(f"Migration output: {result.stderr}")
    except Exception as e:
        logger.warning(f"Migration step skipped: {e}")

    db = SessionLocal()
    results = []

    try:
        plan = _get_or_create_scale_plan(db)
        if not plan:
            logger.error("No 'scale' subscription plan found in DB. Run the app once to seed plans.")
            sys.exit(1)
        logger.info(f"Using plan: {plan.name} (key: {plan.plan_key})")

        for cfg in COMPANIES:
            logger.info(f"\n--- Seeding: {cfg['company_name']} ---")
            result = _seed_company(db, cfg, plan)
            results.append(result)

    except Exception as e:
        db.rollback()
        logger.error(f"Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

    # ── Print credentials ──────────────────────────────────────────────────────
    lines = []
    lines.append("=" * 70)
    lines.append("TEST COMPANY LOGIN CREDENTIALS")
    lines.append("=" * 70)
    lines.append(f"Login endpoint: POST /api/v1/auth/token")
    lines.append(f"Body: {{ \"username\": \"...\", \"password\": \"...\" }}")
    lines.append("")

    for r in results:
        if r.get("skipped"):
            lines.append(f"[{r['company_name']}] — already existed, skipped")
            lines.append("")
            continue

        lines.append(f"INDUSTRY : {r['industry'].upper()}")
        lines.append(f"COMPANY  : {r['company_name']}")
        lines.append(f"CODE     : {r['company_code']}")
        lines.append("")
        lines.append(f"  ADMIN LOGIN")
        lines.append(f"  Username : {r['admin_username']}")
        lines.append(f"  Password : {r['admin_password']}")
        lines.append(f"  Email    : {r['admin_email']}")
        lines.append(f"  Role     : admin (all permissions)")
        lines.append("")
        lines.append(f"  EMPLOYEE LOGINS")
        for emp in r["employees"]:
            lines.append(f"  [{emp['position']}]")
            lines.append(f"    Username : {emp['username']}")
            lines.append(f"    Password : {emp['password']}")
        lines.append("")
        lines.append(f"  PERMISSIONS : ALL modules enabled (inventory, CRM, bookings,")
        lines.append(f"                billing, shifts, donations, AI chat, etc.)")
        lines.append("-" * 70)
        lines.append("")

    lines.append("AI CHAT: The AI knows the industry context automatically.")
    lines.append("  Restaurant AI -> answers kitchen/ingredient/table questions")
    lines.append("  Temple AI     -> answers prasad/donation/pooja questions")
    lines.append("  Hospital AI   -> answers medicine/patient/OPD questions")
    lines.append("=" * 70)

    output = "\n".join(lines)
    print("\n" + output)

    # Save to file
    with open("test_credentials.txt", "w", encoding="utf-8") as f:
        f.write(output)
    logger.info("\nCredentials saved to test_credentials.txt")


if __name__ == "__main__":
    main()
