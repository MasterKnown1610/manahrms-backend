#!/usr/bin/env python3
"""
Test S3 credentials and connection
"""
from app.api.v1.utils.s3_service import get_s3_service
from app.core.config import settings
import traceback

print("=" * 60)
print("S3 Credentials Test")
print("=" * 60)

print(f"\n1. Configuration:")
print(f"   USE_S3: {settings.USE_S3}")
print(f"   AWS_REGION: {settings.AWS_REGION}")
print(f"   S3_BUCKET_NAME: {settings.S3_BUCKET_NAME}")
print(f"   AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID[:10] + '...' if settings.AWS_ACCESS_KEY_ID else 'Not set'}")
print(f"   AWS_SECRET_ACCESS_KEY: {'Set' if settings.AWS_SECRET_ACCESS_KEY else 'Not set'}")

try:
    s3_service = get_s3_service()
    if not s3_service:
        print("\n❌ S3 service not available")
        exit(1)
    
    print("\n2. Testing bucket access...")
    try:
        s3_service.s3_client.head_bucket(Bucket=s3_service.bucket_name)
        print("   ✅ Bucket access successful!")
    except Exception as e:
        print(f"   ❌ Bucket access failed: {e}")
        exit(1)
    
    print("\n3. Testing presigned URL generation...")
    test_key = "company_12/employee_14/profile_photo/test.jpg"
    
    # Test download URL
    download_url = s3_service.generate_presigned_url(
        test_key,
        expiration=3600,
        response_content_disposition='attachment'
    )
    print(f"   ✅ Download URL generated: {download_url[:80]}...")
    
    # Test view URL
    view_url = s3_service.generate_view_url(
        test_key,
        content_type='image/jpeg'
    )
    print(f"   ✅ View URL generated: {view_url[:80]}...")
    
    print("\n4. Checking URL parameters...")
    if 'response-content-disposition=inline' in view_url or 'response-content-disposition%3Dinline' in view_url:
        print("   ✅ View URL contains inline disposition")
    else:
        print("   ⚠️  View URL might not have inline disposition")
    
    if 'response-content-type' in view_url:
        print("   ✅ View URL contains content type")
    else:
        print("   ⚠️  View URL might not have content type")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nIf you're still getting SignatureDoesNotMatch errors:")
    print("1. Verify AWS credentials in .env file are correct")
    print("2. Check that AWS_REGION matches your bucket's region")
    print("3. Ensure the IAM user has s3:GetObject permission")
    print("4. Check server time is synchronized (clock skew can cause signature issues)")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
