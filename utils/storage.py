"""
Загрузка файлов в Cloudflare R2
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.client import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 не установлен — загрузка в R2 недоступна")

from config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
)


def is_r2_configured() -> bool:
    """Проверяет, настроен ли R2"""
    return bool(
        BOTO3_AVAILABLE
        and R2_ACCOUNT_ID
        and R2_ACCESS_KEY_ID
        and R2_SECRET_ACCESS_KEY
        and R2_BUCKET_NAME
        and R2_PUBLIC_URL
    )


def get_s3_client():
    """Создаёт S3-совместимый клиент для R2"""
    if not is_r2_configured():
        raise RuntimeError("R2 не настроен. Проверь переменные окружения.")

    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_to_r2(local_path: str, object_key: str, content_type: str = "video/mp4") -> Optional[str]:
    """
    Загружает файл в R2 и возвращает публичную ссылку.
    
    :param local_path: путь к локальному файлу
    :param object_key: имя объекта в бакете (например movies/film_123.mp4)
    :param content_type: MIME-тип
    :return: публичная URL или None при ошибке
    """
    if not is_r2_configured():
        logger.error("R2 не настроен")
        return None

    if not os.path.exists(local_path):
        logger.error(f"Файл не найден: {local_path}")
        return None

    try:
        client = get_s3_client()
        extra_args = {"ContentType": content_type}

        client.upload_file(
            Filename=local_path,
            Bucket=R2_BUCKET_NAME,
            Key=object_key,
            ExtraArgs=extra_args,
        )

        public_url = f"{R2_PUBLIC_URL}/{object_key}"
        logger.info(f"Файл загружен в R2: {public_url}")
        return public_url

    except Exception as e:
        logger.exception(f"Ошибка загрузки в R2: {e}")
        return None


def delete_from_r2(object_key: str) -> bool:
    """Удаляет объект из R2 (опционально)"""
    if not is_r2_configured():
        return False
    try:
        client = get_s3_client()
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=object_key)
        return True
    except Exception as e:
        logger.exception(f"Ошибка удаления из R2: {e}")
        return False
