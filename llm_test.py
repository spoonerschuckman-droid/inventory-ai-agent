import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.responses.create(
    model="deepseek-flash",
    input="请用一句话告诉我：你已经成功收到这条消息。"
)

print(response.output_text)