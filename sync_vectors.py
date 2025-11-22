"""
Script to sync company data to vector store
Run this to populate embeddings for all companies or a specific company
"""
import sys
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.api.v1.models.company_model import Company
from app.api.v1.services.vector_sync_service import VectorSyncService


def sync_all_companies():
    """Sync vectors for all companies"""
    db: Session = SessionLocal()
    try:
        companies = db.query(Company).filter(Company.is_active == True).all()
        print(f"Found {len(companies)} active companies")
        
        sync_service = VectorSyncService()
        
        for company in companies:
            print(f"\nSyncing company: {company.company_name} (ID: {company.id})")
            stats = sync_service.sync_company_data(db, company.id)
            print(f"  ✅ Employees: {stats['employees']}")
            print(f"  ✅ Projects: {stats['projects']}")
            print(f"  ✅ Tasks: {stats['tasks']}")
            print(f"  ✅ Departments: {stats['departments']}")
            print(f"  ✅ Company: {stats['company']}")
            if stats['errors']:
                print(f"  ⚠️  Errors: {len(stats['errors'])}")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    print(f"     - {error}")
        
        print("\n✅ Sync completed!")
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False
    finally:
        db.close()
    
    return True


def sync_company(company_id: int):
    """Sync vectors for a specific company"""
    db: Session = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            print(f"❌ Company with ID {company_id} not found")
            return False
        
        print(f"Syncing company: {company.company_name} (ID: {company.id})")
        sync_service = VectorSyncService()
        stats = sync_service.sync_company_data(db, company.id)
        
        print(f"  ✅ Employees: {stats['employees']}")
        print(f"  ✅ Projects: {stats['projects']}")
        print(f"  ✅ Tasks: {stats['tasks']}")
        print(f"  ✅ Departments: {stats['departments']}")
        print(f"  ✅ Company: {stats['company']}")
        if stats['errors']:
            print(f"  ⚠️  Errors: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"     - {error}")
        
        print("\n✅ Sync completed!")
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            company_id = int(sys.argv[1])
            sync_company(company_id)
        except ValueError:
            print("❌ Invalid company ID. Usage: python sync_vectors.py [company_id]")
    else:
        sync_all_companies()

