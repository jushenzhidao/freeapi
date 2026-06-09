from openai import OpenAI
client = OpenAI()
res = client.videos.create()
client.chat.completions.create()
res.id
client