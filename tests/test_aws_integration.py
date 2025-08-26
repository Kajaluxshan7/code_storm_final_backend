"""
AWS S3 Integration Tests
Test S3 connectivity, file operations, and configurations
"""
import pytest
import asyncio
import io
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from app.integrations.storage.s3 import S3Storage, s3_storage
from app.integrations.storage.local import LocalStorage, local_storage
from app.core.config import settings


class TestS3Integration:
    """Test AWS S3 integration functionality"""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client for testing"""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def s3_instance(self, mock_s3_client):
        """Create S3Storage instance with mocked client"""
        storage = S3Storage()
        storage.s3_client = mock_s3_client
        return storage
    
    @pytest.mark.asyncio
    async def test_s3_upload_file(self, s3_instance, mock_s3_client):
        """Test S3 file upload functionality"""
        # Prepare test data
        test_file = io.BytesIO(b"test file content")
        object_key = "test/test_file.txt"
        content_type = "text/plain"
        
        # Mock successful upload
        mock_s3_client.upload_fileobj.return_value = None
        
        # Test upload
        result = await s3_instance.upload_file(test_file, object_key, content_type)
        
        # Assertions
        assert result is True
        mock_s3_client.upload_fileobj.assert_called_once()
        
        # Check call arguments
        call_args = mock_s3_client.upload_fileobj.call_args
        assert call_args[0][0] == test_file  # file object
        assert call_args[0][1] == settings.S3_BUCKET_NAME  # bucket
        assert call_args[0][2] == object_key  # key
        assert call_args[1]['ExtraArgs']['ContentType'] == content_type
    
    @pytest.mark.asyncio
    async def test_s3_upload_file_error(self, s3_instance, mock_s3_client):
        """Test S3 file upload error handling"""
        # Prepare test data
        test_file = io.BytesIO(b"test file content")
        object_key = "test/test_file.txt"
        
        # Mock upload error
        mock_s3_client.upload_fileobj.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
            'upload_fileobj'
        )
        
        # Test upload
        result = await s3_instance.upload_file(test_file, object_key)
        
        # Assertions
        assert result is False
        mock_s3_client.upload_fileobj.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_s3_download_file(self, s3_instance, mock_s3_client):
        """Test S3 file download functionality"""
        object_key = "test/test_file.txt"
        local_path = "/tmp/downloaded_file.txt"
        
        # Mock successful download
        mock_s3_client.download_file.return_value = None
        
        # Test download
        result = await s3_instance.download_file(object_key, local_path)
        
        # Assertions
        assert result is True
        mock_s3_client.download_file.assert_called_once_with(
            settings.S3_BUCKET_NAME,
            object_key,
            local_path
        )
    
    @pytest.mark.asyncio
    async def test_s3_delete_file(self, s3_instance, mock_s3_client):
        """Test S3 file deletion functionality"""
        object_key = "test/test_file.txt"
        
        # Mock successful deletion
        mock_s3_client.delete_object.return_value = None
        
        # Test deletion
        result = await s3_instance.delete_file(object_key)
        
        # Assertions
        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key
        )
    
    @pytest.mark.asyncio
    async def test_s3_generate_presigned_url(self, s3_instance, mock_s3_client):
        """Test S3 presigned URL generation"""
        object_key = "test/test_file.txt"
        expiration = 3600
        expected_url = "https://test-bucket.s3.amazonaws.com/test/test_file.txt?presigned=true"
        
        # Mock successful URL generation
        mock_s3_client.generate_presigned_url.return_value = expected_url
        
        # Test URL generation
        result = await s3_instance.generate_presigned_url(object_key, expiration)
        
        # Assertions
        assert result == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': object_key},
            ExpiresIn=expiration
        )
    
    def test_s3_configuration(self):
        """Test S3 configuration settings"""
        assert settings.AWS_ACCESS_KEY_ID is not None
        assert settings.AWS_SECRET_ACCESS_KEY is not None
        assert settings.AWS_REGION is not None
        assert settings.S3_BUCKET_NAME is not None


class TestLocalStorageIntegration:
    """Test local storage integration for development"""
    
    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary local storage instance"""
        return LocalStorage(base_path=str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_local_upload_file(self, temp_storage):
        """Test local file upload functionality"""
        # Prepare test data
        test_content = b"test file content for local storage"
        test_file = io.BytesIO(test_content)
        object_key = "test/local_file.txt"
        
        # Test upload
        result = await temp_storage.upload_file(test_file, object_key)
        
        # Assertions
        assert result is True
        
        # Verify file exists and has correct content
        file_path = temp_storage.base_path / object_key
        assert file_path.exists()
        assert file_path.read_bytes() == test_content
    
    @pytest.mark.asyncio
    async def test_local_delete_file(self, temp_storage):
        """Test local file deletion functionality"""
        # Create test file
        object_key = "test/delete_me.txt"
        test_file = io.BytesIO(b"delete this content")
        await temp_storage.upload_file(test_file, object_key)
        
        # Verify file exists
        file_path = temp_storage.base_path / object_key
        assert file_path.exists()
        
        # Test deletion
        result = await temp_storage.delete_file(object_key)
        
        # Assertions
        assert result is True
        assert not file_path.exists()
    
    @pytest.mark.asyncio
    async def test_local_get_file_path(self, temp_storage):
        """Test local file path retrieval"""
        # Create test file
        object_key = "test/path_test.txt"
        test_file = io.BytesIO(b"path test content")
        await temp_storage.upload_file(test_file, object_key)
        
        # Test path retrieval
        file_path = await temp_storage.get_file_path(object_key)
        
        # Assertions
        assert file_path is not None
        assert object_key.replace('/', '\\') in file_path or object_key in file_path
        
        # Test non-existent file
        non_existent_path = await temp_storage.get_file_path("non/existent/file.txt")
        assert non_existent_path is None


class TestStorageConfiguration:
    """Test storage configuration and environment setup"""
    
    def test_storage_settings(self):
        """Test storage-related configuration settings"""
        assert settings.MAX_FILE_SIZE > 0
        assert len(settings.ALLOWED_FILE_TYPES) > 0
        assert all(ext.startswith('.') for ext in settings.ALLOWED_FILE_TYPES)
    
    def test_file_type_validation(self):
        """Test file type validation logic"""
        allowed_types = settings.ALLOWED_FILE_TYPES
        
        # Test allowed image extensions
        assert '.jpg' in allowed_types
        assert '.jpeg' in allowed_types
        assert '.png' in allowed_types
        assert '.gif' in allowed_types
        assert '.bmp' in allowed_types
        assert '.tiff' in allowed_types
        assert '.webp' in allowed_types
        assert '.svg' in allowed_types
        
        # Test file size limit is 20MB
        assert settings.MAX_FILE_SIZE == 20 * 1024 * 1024  # 20MB
