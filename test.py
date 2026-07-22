import time

from app.core.storage import get_minio_client,upload_image
if __name__ == '__main__':
    client = get_minio_client(net=None)
    with open(r'C:\Users\16239\Downloads\00895c9c-4d0c-4ed7-9766-c231196a508c.png', "rb") as f:
        data = f.read()
    import io
    data = io.BytesIO(data)
    print(upload_image(client, data,file_type='png',content_type='image/png'))
    # import json
    # from minio import Minio

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
#     from app.schemas.chat import ChatRequest
#     import json
#     x = json.loads('''{
#   "model": "nano-banana",
#   "stream": false,
#   "messages": [
#     {
#       "role": "user",
#       "content": [
#         {
#           "type": "text",
#           "text": "带个墨镜"
#         },
#         {
#           "type": "image_url",
#           "image_url": {
#             "url": "https://oss.ffire.cc/files/kling_watermark.png"
#           }
#         }
#       ]
#     }
#   ]
# }''')
#     c = ChatRequest.model_validate(x)
    # print(c.model_dump(exclude_none=True))
