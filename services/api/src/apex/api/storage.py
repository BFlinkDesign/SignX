"""MinIO/S3 storage client for file uploads."""

from __future__ import annotations

from typing import Optional

import structlog
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)


class StorageClient:
    """MinIO/S3 storage client wrapper."""

    def __init__(
        self,
        endpoint: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        """Initialize storage client."""
        self.endpoint = endpoint
        self.bucket = bucket or "apex-uploads"
        self._client: Optional[object] = None
        
        # Parse endpoint
        parsed = urlparse(endpoint)
        self.is_secure = parsed.scheme == "https"
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port
        
        # Initialize client if credentials provided
        if access_key and secret_key:
            try:
                from minio import Minio
                
                self._client = Minio(
                    f"{self.host}:{self.port or (443 if self.is_secure else 9000)}",
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=self.is_secure,
                )
                
                # Ensure bucket exists
                if not self._client.bucket_exists(self.bucket):
                    self._client.make_bucket(self.bucket)
                    logger.info("storage.bucket_created", bucket=self.bucket)
                    
                logger.info("storage.client_initialized", bucket=self.bucket)
            except ImportError:
                logger.warning("storage.minio_not_available", reason="minio package not installed")
            except Exception as e:
                logger.warning("storage.client_failed", error=str(e))
    
    def presign_put(
        self,
        object_name: str,
        expires_seconds: int = 3600,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """Generate presigned PUT URL for upload.
        
        Returns None if client not available.
        """
        if not self._client:
            return None
        
        try:
            from datetime import timedelta
            
            url = self._client.presigned_put_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds),
            )
            return url
        except Exception as e:
            logger.error("storage.presign_failed", object_name=object_name, error=str(e))
            return None
    
    def get_object_sha256(self, object_name: str) -> Optional[str]:
        """Get SHA256 hash of stored object.
        
        Returns None if client not available or object not found.
        """
        if not self._client:
            return None
        
        try:
            import hashlib
            
            # Stream object and compute hash
            response = self._client.get_object(self.bucket, object_name)
            hasher = hashlib.sha256()
            
            for chunk in response.stream(8192):
                hasher.update(chunk)
            
            response.close()
            response.release_conn()
            
            return hasher.hexdigest()
        except Exception as e:
            logger.error("storage.sha256_failed", object_name=object_name, error=str(e))
            return None
    
    def object_exists(self, object_name: str) -> bool:
        """Check if object exists in storage."""
        if not self._client:
            return False
        
        try:
            from minio.error import S3Error
            
            self._client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False
        except Exception as e:
            logger.error("storage.exists_failed", object_name=object_name, error=str(e))
            return False

