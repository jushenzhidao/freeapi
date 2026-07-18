import time

from app.core.storage import get_minio_client,upload_image
if __name__ == '__main__':
    client = get_minio_client(net='cn')
    with open(r'C:\Users\16239\Downloads\00895c9c-4d0c-4ed7-9766-c231196a508c.png', "rb") as f:
        data = f.read()
    import io
    data = io.BytesIO(data)
    print(upload_image(client, data))
    import json
    from minio import Minio

    # client = Minio("localhost:9000", access_key="你的AK", secret_key="你的SK", secure=False)
    # # 桶设为公开
    # policy = {
    #     "Version": "2012-10-17",
    #     "Statement": [{
    #         "Effect": "Allow",
    #         "Principal": {"AWS": ["*"]},
    #         "Action": ["s3:GetObject"],
    #         "Resource": ["arn:aws:s3:::cdn/*"],
    #     }],
    # }
    # client.set_bucket_policy("cdn", json.dumps(policy))
