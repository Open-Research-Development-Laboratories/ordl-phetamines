from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class StorageAdapter:
    def put_text(self, key: str, content: str) -> str:
        raise NotImplementedError


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_text(self, key: str, content: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return str(path)


class S3StorageAdapter(StorageAdapter):
    def __init__(self, bucket: str) -> None:
        import boto3

        self.bucket = bucket
        self.client = boto3.client('s3')

    def put_text(self, key: str, content: str) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content.encode('utf-8'), ContentType='text/plain')
        return f's3://{self.bucket}/{key}'


def get_storage_adapter() -> StorageAdapter:
    settings = get_settings()
    if settings.storage_backend.lower() == 's3':
        return S3StorageAdapter(bucket=settings.storage_bucket)
    return LocalStorageAdapter(root=settings.storage_local_root)
