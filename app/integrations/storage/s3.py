"""
S3 Storage Integration
AWS S3 or S3-compatible storage for file uploads
"""
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """S3 storage client for file operations"""
    
    def __init__(self):
        # Create a boto3 Session. If explicit credentials are provided in
        # settings, pass them; otherwise let boto3 use the default credential
        # chain (environment, shared credentials file, or instance profile).
        aws_key = settings.AWS_ACCESS_KEY_ID or None
        aws_secret = settings.AWS_SECRET_ACCESS_KEY or None
        region = settings.AWS_REGION or None

        if aws_key and aws_secret:
            self.session = boto3.Session(
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=region,
            )
        else:
            # Use default credential lookup (recommended for production on AWS)
            self.session = boto3.Session(region_name=region)

        # Build client kwargs only when needed (avoid passing None endpoint)
        client_kwargs = {}
        if settings.S3_ENDPOINT_URL:
            client_kwargs['endpoint_url'] = settings.S3_ENDPOINT_URL

        self.s3_client = self.session.client('s3', **client_kwargs)
        self.bucket_name = settings.S3_BUCKET_NAME
    
    async def upload_file(
        self, 
        file_obj: BinaryIO, 
        object_key: str,
        content_type: Optional[str] = None
    ) -> bool:
        """
        Upload file to S3 bucket
        
        Args:
            file_obj: File object to upload
            object_key: S3 object key (file path in bucket)
            content_type: MIME type of the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"File uploaded successfully: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
    
    async def download_file(self, object_key: str, local_path: str) -> bool:
        """
        Download file from S3 bucket
        
        Args:
            object_key: S3 object key
            local_path: Local file path to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                local_path
            )
            
            logger.info(f"File downloaded successfully: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
    
    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3 bucket
        
        Args:
            object_key: S3 object key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"File deleted successfully: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    async def generate_presigned_url(
        self, 
        object_key: str, 
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for file access
        
        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            str: Presigned URL or None if error
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None


# Global S3 storage instance
s3_storage = S3Storage()
