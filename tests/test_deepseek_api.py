#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试DeepSeek API连接
"""

import os
import requests
import json

def test_deepseek_api():
    """测试DeepSeek API连接"""
    
    # 获取API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 未找到DEEPSEEK_API_KEY环境变量")
        return False
    
    print(f"✅ 找到API密钥: {api_key[:10]}...")
    
    # API端点
    endpoint = "https://api.deepseek.com/chat/completions"
    
    # 请求头
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 测试消息
    data = {
        'model': 'deepseek-reasoner',
        'messages': [
            {
                'role': 'user',
                'content': '你好，请简单介绍一下你自己。'
            }
        ],
        'max_tokens': 100,
        'temperature': 0.7,
        'stream': False
    }
    
    try:
        print("🔄 正在测试DeepSeek API连接...")
        response = requests.post(
            endpoint, 
            headers=headers, 
            json=data,
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API连接成功！")
            print(f"📝 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ API调用失败")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API调用异常: {e}")
        return False

if __name__ == "__main__":
    test_deepseek_api()