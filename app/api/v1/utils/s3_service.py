"""
S3 service for handling file uploads, downloads, and deletions
"""
from typing import Optional, BinaryIO
import logging
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy import boto3 - only import when S3 is actually used
try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    from botocore.config import Config as BotoConfig
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 is not installed. S3 functionality will not be available. Install it with: pip install boto3")


class S3Service:
    """Service for interacting with AWS S3"""
    
    def __init__(self):
        """Initialize S3 client"""
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is not installed. Install it with: pip install boto3")
        
        if not settings.USE_S3:
            raise ValueError("S3 is not enabled. Set USE_S3=True in settings.")
        
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME is required when USE_S3=True")
        
        # Initialize S3 client
        s3_config = {
            'region_name': settings.AWS_REGION,
        }
        
        # Add credentials if provided
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            s3_config['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            s3_config['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        else:
            # If credentials not provided, boto3 will use default credential chain
            # (environment variables, IAM role, etc.)
            logger.info("AWS credentials not provided, using default credential chain")
        
        # Add custom endpoint if provided (for S3-compatible services)
        if settings.S3_ENDPOINT_URL:
            s3_config['endpoint_url'] = settings.S3_ENDPOINT_URL
        
        # Configure signature version for better compatibility
        s3_config['config'] = BotoConfig(
            signature_version='s3v4',
            s3={'addressing_style': 'virtual'}  # Use virtual-hosted-style URLs
        )
        
        self.s3_client = boto3.client('s3', **s3_config)
        self.bucket_name = settings.S3_BUCKET_NAME
        
        # Verify credentials by checking if we can access the bucket
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '403':
                logger.error(f"Access denied to S3 bucket {self.bucket_name}. Check your AWS credentials and permissions.")
            elif error_code == '404':
                logger.error(f"S3 bucket {self.bucket_name} not found. Check bucket name and region.")
            else:
                logger.warning(f"Could not verify S3 bucket access: {e}")
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        content_type: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3
        
        Args:
            file_obj: File-like object to upload
            s3_key: S3 object key (path in bucket)
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
            
        Returns:
            S3 key of the uploaded file
            
        Raises:
            HTTPException: If upload fails
        """
        try:
            extra_args = {
                'ContentType': content_type,
            }
            
            if metadata:
                extra_args['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Successfully uploaded file to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to S3: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading file to S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
    
    def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            File content as bytes, or None if file doesn't exist
            
        Raises:
            HTTPException: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in S3: {s3_key}")
                return None
            logger.error(f"Error downloading file from S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file from S3: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error downloading file from S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}"
            )
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Successfully deleted file from S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file from S3: {str(e)}")
            return False
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        content_type: Optional[str] = None,
        response_content_disposition: Optional[str] = None
    ) -> str:
        """
        Generate a presigned URL for downloading or viewing a file
        
        Args:
            s3_key: S3 object key (path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)
            content_type: Optional content type for the response
            response_content_disposition: Optional content disposition (e.g., 'inline' for viewing, 'attachment' for download)
            
        Returns:
            Presigned URL string
            
        Raises:
            HTTPException: If URL generation fails
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
            }
            
            if content_type:
                params['ResponseContentType'] = content_type
            
            if response_content_disposition:
                params['ResponseContentDisposition'] = response_content_disposition
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate URL: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate URL: {str(e)}"
            )
    
    def generate_view_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """
        Generate a presigned URL for viewing a file inline (e.g., in img tag)
        
        Args:
            s3_key: S3 object key (path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)
            content_type: Optional content type for the response
            
        Returns:
            Presigned URL string suitable for inline viewing
            
        Raises:
            HTTPException: If URL generation fails
        """
        return self.generate_presigned_url(
            s3_key=s3_key,
            expiration=expiration,
            content_type=content_type,
            response_content_disposition='inline'
        )
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            logger.error(f"Error checking file existence in S3: {str(e)}")
            return False


def get_s3_service() -> Optional[S3Service]:
    """
    Get S3 service instance if S3 is enabled
    
    Returns:
        S3Service instance if enabled, None otherwise
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 is not installed. S3 functionality is not available.")
        return None
    
    if settings.USE_S3:
        try:
            return S3Service()
        except Exception as e:
            logger.error(f"Failed to initialize S3 service: {str(e)}")
            return None
    return None
