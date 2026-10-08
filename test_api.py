#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 DeepSeek API 连接"""

import os
import requests
import json
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 获取API密钥
api_key = os.environ.get("DEEPSEEK_API_KEY")
print(f"API Key: {api_key[:20]}..." if api_key else "未找到API Key")

if not api_key:
    print("❌ 错误: 未设置 DEEPSEEK_API_KEY 环境变量")
    exit(1)

# API配置
endpoint = "https://api.deepseek.com/chat/completions"
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

# 测试消息
messages = [
    {"role": "system", "content": "你是一个助手。"},
    {"role": "user", "content": "你好，请回复'测试成功'"}
]

data = {
    'model': 'deepseek-reasoner',
    'messages': messages,
    'max_tokens': 100,
    'temperature': 0.7,
    'stream': False
}

print(f"\n🔄 正在测试 DeepSeek API...")
print(f"Endpoint: {endpoint}")
print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

try:
    response = requests.post(
        endpoint,
        headers=headers,
        json=data,
        timeout=60
    )
    
    print(f"\n📊 状态码: {response.status_code}")
    print(f"📄 响应内容:\n{response.text}")
    
    if response.status_code == 200:
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            print(f"\n✅ API 测试成功!")
            print(f"返回内容: {content}")
        else:
            print(f"\n⚠️ API 返回格式异常")
    else:
        print(f"\n❌ API 调用失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        
except Exception as e:
    print(f"\n❌ API 调用异常: {e}")
