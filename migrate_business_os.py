"""
Migration script — creates all new Business OS tables without touching existing ones.
Run once: python migrate_business_os.py

Safe to re-run (uses CREATE TABLE IF NOT EXISTS via SQLAlchemy checkfirst=True).
Does NOT drop or alter any existing table.
"""
import sys
import logging
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run():
    from app.core.config import settings
    from app.db.session import engine
    from app.db.base import Base

    # Import new models so they register with Base.metadata
    from app.api.v1.models.company_profile_model import CompanyProfile
    from app.api.v1.models.inventory_model import InventoryCategory, InventoryItem, InventoryTransaction
    from app.api.v1.models.asset_model import Asset, AssetAssignment, AssetMaintenanceLog
    from app.api.v1.models.crm_model import Client, ClientInteraction
    from app.api.v1.models.booking_model import BookingResource, Booking
    from app.api.v1.models.billing_ops_model import Invoice, InvoiceItem
    from app.api.v1.models.shift_model import Shift, ShiftAssignment
    from app.api.v1.models.donation_model import Donation

    new_tables = [
        "company_profiles",
        "inventory_categories",
        "inventory_items",
        "inventory_transactions",
        "assets",
        "asset_assignments",
        "asset_maintenance_logs",
        "crm_clients",
        "crm_interactions",
        "booking_resources",
        "bookings",
        "invoices",
        "invoice_items",
        "shifts",
        "shift_assignments",
        "donations",
    ]

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    logger.info("=== ManaHRMS Business OS Migration ===")
    logger.info(f"Database: {settings.DATABASE_URL[:50]}...")

    tables_to_create = [t for t in new_tables if t not in existing_tables]
    already_exist = [t for t in new_tables if t in existing_tables]

    if already_exist:
        logger.info(f"Already exist (skipping): {', '.join(already_exist)}")

    if not tables_to_create:
        logger.info("All Business OS tables already exist. Nothing to do.")
        return

    logger.info(f"Creating tables: {', '.join(tables_to_create)}")

    # Create only the new tables — checkfirst=True skips existing ones
    Base.metadata.create_all(engine, checkfirst=True, tables=[
        Base.metadata.tables[t] for t in new_tables if t in Base.metadata.tables
    ])

    # Verify
    inspector2 = inspect(engine)
    created = inspector2.get_table_names()
    for t in tables_to_create:
        if t in created:
            logger.info(f"  ✓ {t}")
        else:
            logger.error(f"  ✗ {t} — FAILED TO CREATE")

    logger.info("Migration complete.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
