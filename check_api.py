from openai import OpenAI

client = OpenAI(
  base_url="https://apis.iflow.cn/v1",
  api_key="sk-088054b6de0f377b750ba984dd6e0eb5",
)

completion = client.chat.completions.create(
  extra_body={},
  model="qwen3-max",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)
print(completion.choices[0].message.content)