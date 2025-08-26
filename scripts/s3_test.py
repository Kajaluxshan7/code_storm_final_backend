"""Simple S3 smoke-test script: upload, list, download, delete"""
import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError

# Add the project root to Python path to import app modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.config import settings
import boto3

BUCKET = settings.S3_BUCKET_NAME
KEY = "s3_test_sample.txt"
LOCAL_FILE = "s3_test_sample.txt"
DOWNLOAD_FILE = "s3_test_downloaded.txt"


def get_s3_client():
    kwargs = {}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
        kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
    if settings.S3_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.S3_ENDPOINT_URL
    if settings.AWS_REGION:
        kwargs['region_name'] = settings.AWS_REGION
    return boto3.client('s3', **kwargs)


def test_s3_permissions():
    """Test S3 permissions before running full test"""
    try:
        s3 = get_s3_client()
        
        print("=== S3 Connection Test ===")
        print(f"Bucket: {BUCKET}")
        print(f"Region: {settings.AWS_REGION}")
        print(f"Endpoint: {settings.S3_ENDPOINT_URL or 'Default AWS'}")
        
        # Test bucket access
        print("\n=== Testing Bucket Access ===")
        try:
            response = s3.head_bucket(Bucket=BUCKET)
            print("✅ Bucket access: SUCCESS")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print("❌ Bucket access: FAILED - Bucket does not exist")
                return False
            elif error_code == '403':
                print("❌ Bucket access: FAILED - Access denied")
                return False
            else:
                print(f"❌ Bucket access: FAILED - {error_code}: {e}")
                return False
        
        # Test list permissions
        print("\n=== Testing List Permissions ===")
        try:
            s3.list_objects_v2(Bucket=BUCKET, MaxKeys=1)
            print("✅ List objects: SUCCESS")
        except ClientError as e:
            print(f"❌ List objects: FAILED - {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        
        # Test upload permissions (dry run)
        print("\n=== Testing Upload Permissions ===")
        test_content = "S3 permission test"
        try:
            s3.put_object(Bucket=BUCKET, Key="permission_test.txt", Body=test_content)
            print("✅ Upload permission: SUCCESS")
            
            # Clean up test object
            try:
                s3.delete_object(Bucket=BUCKET, Key="permission_test.txt")
                print("✅ Delete permission: SUCCESS")
            except ClientError as e:
                print(f"⚠️ Delete permission: WARNING - {e.response['Error']['Code']}")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                print("❌ Upload permission: FAILED - Access denied")
                print("   Required permissions: s3:PutObject")
            else:
                print(f"❌ Upload permission: FAILED - {error_code}: {e.response['Error']['Message']}")
            return False
            
    except NoCredentialsError:
        print("❌ AWS credentials not found")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    print("=== S3 Configuration ===")
    print(f"AWS Access Key ID: {'✅ Set' if settings.AWS_ACCESS_KEY_ID else '❌ Not set'}")
    print(f"AWS Secret Key: {'✅ Set' if settings.AWS_SECRET_ACCESS_KEY else '❌ Not set'}")
    print(f"S3 Bucket: {settings.S3_BUCKET_NAME or '❌ Not set'}")
    print(f"AWS Region: {settings.AWS_REGION or '❌ Not set'}")
    
    if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.S3_BUCKET_NAME]):
        print("\n❌ Missing required AWS configuration. Please check your environment variables.")
        return
    
    # Test permissions first
    if not test_s3_permissions():
        print("\n❌ Permission test failed. Cannot proceed with full S3 test.")
        return
    
    print("\n=== Running Full S3 Test ===")
    s3 = get_s3_client()

    # create a small local test file
    with open(LOCAL_FILE, 'w') as f:
        f.write('s3 test content with timestamp: ' + str(os.path.getmtime(__file__)))

    try:
        print(f"Uploading {LOCAL_FILE} to bucket {BUCKET} as {KEY}...")
        s3.upload_file(LOCAL_FILE, BUCKET, KEY)
        print("✅ Upload complete")

        print("Listing objects in bucket:")
        resp = s3.list_objects_v2(Bucket=BUCKET)
        for obj in resp.get('Contents', []):
            print(' -', obj['Key'])

        print(f"Downloading {KEY} to {DOWNLOAD_FILE}...")
        s3.download_file(BUCKET, KEY, DOWNLOAD_FILE)
        print('✅ Download complete')

        print('Deleting test object...')
        s3.delete_object(Bucket=BUCKET, Key=KEY)
        print('✅ Delete complete')

        print("\n🎉 All S3 operations successful!")

    except ClientError as e:
        print(f"❌ S3 operation failed: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # cleanup local files
        for file_path in [LOCAL_FILE, DOWNLOAD_FILE]:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up {file_path}")


if __name__ == '__main__':
    main()
