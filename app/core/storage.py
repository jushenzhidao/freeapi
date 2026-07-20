
import uuid
import time

from functools import lru_cache
from minio import Minio
from app.core.config import get_settings

@lru_cache
def get_minio_client(net = None) -> Minio:
    s = get_settings()
    if net=='cn':
        minio_endpoint = s.minio_endpoint_cn
    else:
        minio_endpoint = s.minio_endpoint
    return Minio(
        minio_endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=s.minio_secure,
    )

def upload_image(client: Minio, data, file_type='jpg',content_type: str='image/jpg') -> str:

    object_name = f"{time.strftime('%Y%m%d')}/{uuid.uuid4().hex}.{file_type}"
    # 先 seek(0,2) 拿到流的大小，再 seek(0) 把游标移回开头
    # ⚠️ 不重置游标会导致 put_object 从 EOF 读起 → "expected N, got: 0 bytes"
    length = data.seek(0, 2) or 0
    data.seek(0)
    client.put_object(
        bucket_name=get_settings().minio_bucket,
        object_name=object_name,
        data=data,
        length=length,
        content_type=content_type,
    )
    # 桶是 public-read（裸 URL 已验证 200），预签名签名参数多余 -> 生成后去掉 ? 起的签名部分
    # 这样 host/路径前缀(如 /cdn/)由 MinIO 自己算对，无需硬编码 CDN 域名
    signed_url = client.presigned_get_object(get_settings().minio_bucket, object_name)
    url = signed_url.split("?", 1)[0]
    return url

