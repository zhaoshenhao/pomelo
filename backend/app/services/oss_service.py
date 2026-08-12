import asyncio
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import oss2

    _oss2_available = True
except ImportError:
    _oss2_available = False
    logger.warning("oss2 not installed; OSS features unavailable")


def oss_configured() -> bool:
    return (
        _oss2_available
        and bool(settings.OSS_ACCESS_KEY_ID)
        and bool(settings.OSS_ACCESS_KEY_SECRET)
        and bool(settings.OSS_BUCKET)
    )


def _get_bucket(endpoint: str):
    if not _oss2_available:
        raise RuntimeError("oss2 not installed")
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, endpoint, settings.OSS_BUCKET, connect_timeout=5)


def _internal_bucket():
    return _get_bucket(settings.OSS_ENDPOINT_INTERNAL)


def _public_bucket():
    return _get_bucket(settings.OSS_ENDPOINT_PUBLIC)


def object_exists(key: str) -> bool:
    if not oss_configured():
        return False
    bucket = _internal_bucket()
    return bucket.object_exists(key)


def list_first_level_dirs() -> list[str]:
    if not oss_configured():
        return []
    bucket = _internal_bucket()
    prefix = settings.OSS_VIDEO_PREFIX
    dirs = set()
    for obj in oss2.ObjectIteratorV2(bucket, prefix=prefix, delimiter="/"):
        if obj.is_prefix():
            name = obj.key[len(prefix):].rstrip("/")
            if name:
                dirs.add(name)
    return sorted(dirs)


def list_objects(prefix: str = "") -> list[dict]:
    if not oss_configured():
        return []
    bucket = _internal_bucket()
    full_prefix = settings.OSS_VIDEO_PREFIX + prefix
    objects = []
    for obj in oss2.ObjectIteratorV2(bucket, prefix=full_prefix):
        if not obj.is_prefix():
            key = obj.key
            name = key[len(settings.OSS_VIDEO_PREFIX):]
            objects.append({"key": key, "name": name, "size": obj.size})
    return objects


def upload(key: str, file_obj, size: int | None = None) -> None:
    if not oss_configured():
        raise RuntimeError("OSS 未配置")
    bucket = _internal_bucket()
    if isinstance(file_obj, bytes):
        # Write bytes to temp file so resumable_upload can use the file path
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        try:
            tmp.write(file_obj)
            tmp.close()
            if size is not None and size > 1024 * 1024:
                oss2.resumable_upload(bucket, key, tmp.name)
            else:
                result = bucket.put_object(key, file_obj)
                if result.status != 200:
                    raise RuntimeError(f"OSS upload failed: {result.status}")
        finally:
            os.unlink(tmp.name)
    else:
        if size is not None and size > 1024 * 1024:
            oss2.resumable_upload(bucket, key, file_obj)
        else:
            result = bucket.put_object(key, file_obj)
            if result.status != 200:
                raise RuntimeError(f"OSS upload failed: {result.status}")


def delete_object(key: str) -> None:
    if not oss_configured():
        raise RuntimeError("OSS 未配置")
    bucket = _internal_bucket()
    bucket.delete_object(key)


def sign_url(key: str, expires: int = 3600) -> str:
    bucket = _public_bucket()
    return bucket.sign_url("GET", key, expires, slash_safe=True)


def download_to_temp(key: str) -> str:
    if not oss_configured():
        raise RuntimeError("OSS 未配置")
    import tempfile

    bucket = _internal_bucket()
    suffix = ".mp4"
    if "." in key.rsplit("/", 1)[-1]:
        suffix = "." + key.rsplit(".", 1)[-1]
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    bucket.get_object_to_file(key, tmp.name)
    tmp.close()
    return tmp.name


# Async wrappers — run blocking OSS calls in thread pool

async def list_first_level_dirs_async() -> list[str]:
    return await asyncio.to_thread(list_first_level_dirs)


async def list_objects_async(prefix: str = "") -> list[dict]:
    return await asyncio.to_thread(list_objects, prefix)


async def object_exists_async(key: str) -> bool:
    return await asyncio.to_thread(object_exists, key)


async def upload_async(key: str, file_obj, size: int | None = None) -> None:
    return await asyncio.to_thread(upload, key, file_obj, size)


async def delete_object_async(key: str) -> None:
    return await asyncio.to_thread(delete_object, key)


async def download_to_temp_async(key: str) -> str:
    return await asyncio.to_thread(download_to_temp, key)
