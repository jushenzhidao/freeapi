import time

from app.core.storage import get_minio_client,upload_image
if __name__ == '__main__':
    client = get_minio_client()
    with open(r'C:\Users\16239\Downloads\00895c9c-4d0c-4ed7-9766-c231196a508c.png', "rb") as f:
        data = f.read()
    import base64
    import requests
    import json

    # url = "https://uqapi.com/v1beta/models/gemini-3.1-flash-lite-image:generateContent"
    # t1 = time.time()
    # payload = json.dumps({
    #     "contents": [
    #         {
    #             "role": "user",
    #             "parts": [
    #                 {
    #                     "text": "国风汉服少女"
    #                 }
    #             ]
    #         }
    #     ],
    #     "generationConfig": {
    #         "responseModalities": [
    #             "TEXT",
    #             "IMAGE"
    #         ],
    #         "imageConfig": {
    #             "aspectRatio": "16:9",
    #             "imageSize": "1K"
    #         },
    #         "responseFormat": {
    #             "image": {
    #                 "delivery": "URI"
    #             }
    #         }
    #     }
    # })
    # headers = {
    #     'Authorization': 'Bearer sk-MBAfSiz1oYw56ZXBeEMFrLsV3iOLDR0jfQEJnwPCGw4iyFok',
    #     'Content-Type': 'application/json'
    # }
    #
    # response = requests.request("POST", url, headers=headers, data=payload)
    #
    # data = response.json()
    # base64_data = base64.b64decode(data['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    # import io
    # data = io.BytesIO(base64_data)
    # print(len(data))
    import io
    data = io.BytesIO(data)
    print(upload_image(client, data))
    # t2 = time.time()
    # print(t2 - t1)