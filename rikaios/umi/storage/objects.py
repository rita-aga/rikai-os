"""
Object Storage Adapter for Umi

Handles file storage using S3-compatible object storage (MinIO, S3, R2).
Uses aioboto3 for proper async I/O operations.
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
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        region: str = "us-east-1",
    ) -> None:
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._secure = secure
        self._region = region
        self._session: aioboto3.Session | None = None
        self._client_context = None
        self._client = None

    async def connect(self) -> None:
        """Connect to object storage."""
        protocol = "https" if self._secure else "http"
        endpoint_url = f"{protocol}://{self._endpoint}"

        self._session = aioboto3.Session()

        # Create client context manager
        self._client_context = self._session.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

        # Enter the context to get the actual client
        self._client = await self._client_context.__aenter__()

        # Ensure bucket exists
        try:
            await self._client.head_bucket(Bucket=self._bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                await self._client.create_bucket(Bucket=self._bucket)
            else:
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
