"""
Object Storage Adapter for Umi

Handles file storage using S3-compatible object storage (MinIO, S3, R2).
Uses aioboto3 for proper async I/O operations.

Supports two modes:
1. MinIO/local: Uses explicit endpoint and credentials
2. AWS S3: Uses IAM role authentication (no credentials needed)

Usage (MinIO):
    adapter = ObjectAdapter(
        endpoint="localhost:9000",
        access_key="minio",
        secret_key="minio123",
        bucket="my-bucket",
    )

Usage (AWS S3 with IAM role):
    adapter = ObjectAdapter(
        bucket="my-bucket",
        region="us-west-2",
        use_iam_role=True,
    )
"""

import hashlib
import logging
from datetime import datetime, UTC
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ObjectAdapter:
    """
    Async S3-compatible object storage adapter for Umi.

    Uses aioboto3 for non-blocking async operations.
    Supports both MinIO (local) and AWS S3 (with IAM role).
    """

    def __init__(
        self,
        bucket: str,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        secure: bool = True,
        region: str = "us-west-2",
        use_iam_role: bool = False,
    ) -> None:
        """
        Initialize object storage adapter.

        Args:
            bucket: S3 bucket name
            endpoint: Custom endpoint for MinIO/S3-compatible storage (None for AWS S3)
            access_key: AWS access key (None if using IAM role)
            secret_key: AWS secret key (None if using IAM role)
            secure: Use HTTPS (default True)
            region: AWS region (default us-west-2)
            use_iam_role: Use IAM role for authentication (for AWS ECS/EC2)
        """
        self._bucket = bucket
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._secure = secure
        self._region = region
        self._use_iam_role = use_iam_role
        self._session: aioboto3.Session | None = None
        self._client_context = None
        self._client = None

    async def connect(self) -> None:
        """Connect to object storage."""
        self._session = aioboto3.Session()

        # Build client configuration
        client_kwargs: dict[str, Any] = {
            "region_name": self._region,
        }

        if self._use_iam_role:
            # AWS S3 with IAM role - no explicit credentials
            # boto3 will automatically use the ECS task role or EC2 instance profile
            logger.info(f"Using IAM role for S3 access (bucket: {self._bucket})")
        elif self._endpoint:
            # MinIO or S3-compatible storage with explicit credentials
            protocol = "https" if self._secure else "http"
            client_kwargs["endpoint_url"] = f"{protocol}://{self._endpoint}"
            client_kwargs["aws_access_key_id"] = self._access_key
            client_kwargs["aws_secret_access_key"] = self._secret_key
            client_kwargs["config"] = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
            logger.info(f"Using MinIO/S3-compatible storage at {self._endpoint}")
        else:
            # AWS S3 with explicit credentials
            client_kwargs["aws_access_key_id"] = self._access_key
            client_kwargs["aws_secret_access_key"] = self._secret_key
            logger.info(f"Using AWS S3 with explicit credentials (bucket: {self._bucket})")

        # Create client context manager
        self._client_context = self._session.client("s3", **client_kwargs)

        # Enter the context to get the actual client
        self._client = await self._client_context.__aenter__()

        # Ensure bucket exists (skip for IAM role as bucket should pre-exist)
        try:
            await self._client.head_bucket(Bucket=self._bucket)
            logger.info(f"Connected to bucket: {self._bucket}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404" and not self._use_iam_role:
                # Only create bucket for local/MinIO storage
                await self._client.create_bucket(Bucket=self._bucket)
                logger.info(f"Created bucket: {self._bucket}")
            else:
                logger.error(f"Failed to access bucket {self._bucket}: {e}")
                raise

    async def disconnect(self) -> None:
        """Disconnect from object storage."""
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None
        self._client = None
        self._session = None

    async def health_check(self) -> bool:
        """Check if object storage is healthy."""
        if not self._client:
            return False
        try:
            await self._client.head_bucket(Bucket=self._bucket)
            return True
        except Exception as e:
            logger.warning(f"Object storage health check failed: {e}")
            return False

    async def store(
        self,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
        key: str | None = None,
    ) -> str:
        """
        Store content in object storage.

        Args:
            content: Raw bytes to store
            content_type: MIME type of the content
            metadata: Optional metadata dict
            key: Optional specific key; if not provided, generates one

        Returns:
            The object key
        """
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        # Generate key if not provided
        if not key:
            key = self._generate_key(content, content_type)

        # Convert metadata values to strings (S3 requirement)
        s3_metadata = {}
        if metadata:
            for k, v in metadata.items():
                s3_metadata[k] = str(v) if not isinstance(v, str) else v

        # Upload
        await self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=s3_metadata,
        )

        return key

    async def get(self, key: str) -> bytes | None:
        """
        Get content from object storage.

        Args:
            key: Object key

        Returns:
            Raw bytes or None if not found
        """
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        try:
            response = await self._client.get_object(
                Bucket=self._bucket,
                Key=key,
            )
            # Read the body asynchronously
            async with response["Body"] as stream:
                return await stream.read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                return None
            raise

    async def delete(self, key: str) -> bool:
        """
        Delete an object.

        Args:
            key: Object key

        Returns:
            True if deleted, False if not found
        """
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        try:
            await self._client.delete_object(
                Bucket=self._bucket,
                Key=key,
            )
            return True
        except ClientError as e:
            logger.warning(f"Failed to delete object {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if an object exists."""
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        try:
            await self._client.head_object(
                Bucket=self._bucket,
                Key=key,
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        List objects with optional prefix.

        Args:
            prefix: Optional prefix to filter objects
            limit: Maximum number of objects to return

        Returns:
            List of object info dicts with keys: key, size, last_modified
        """
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        response = await self._client.list_objects_v2(
            Bucket=self._bucket,
            Prefix=prefix,
            MaxKeys=limit,
        )

        objects = []
        for obj in response.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"],
            })

        return objects

    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """
        Get object metadata.

        Args:
            key: Object key

        Returns:
            Metadata dict or None if not found
        """
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        try:
            response = await self._client.head_object(
                Bucket=self._bucket,
                Key=key,
            )
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return None
            raise

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for object access.

        Args:
            key: Object key
            expires_in: URL expiration in seconds (default 1 hour)
            method: S3 method ('get_object' or 'put_object')

        Returns:
            Presigned URL
        """
        if not self._client:
            raise RuntimeError("Not connected to object storage")

        url = await self._client.generate_presigned_url(
            ClientMethod=method,
            Params={
                "Bucket": self._bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )
        return url

    def _generate_key(self, content: bytes, content_type: str) -> str:
        """Generate a unique key for content."""
        # Create hash of content
        content_hash = hashlib.sha256(content).hexdigest()[:16]

        # Determine extension from content type
        ext_map = {
            "text/plain": ".txt",
            "text/markdown": ".md",
            "text/html": ".html",
            "application/json": ".json",
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
        }
        ext = ext_map.get(content_type, "")

        # Generate key with date prefix for organization
        now = datetime.now(UTC)
        return f"{now.year}/{now.month:02d}/{now.day:02d}/{content_hash}{ext}"
