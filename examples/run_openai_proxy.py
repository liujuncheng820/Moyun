"""
中文VibeWriting - DeepSeek Reasoner API代理服务器
提供与OpenAI兼容的API接口，转发请求到DeepSeek Reasoner
"""
import os

from fastapi import FastAPI, Request, APIRouter
import httpx

app   = FastAPI()
router = APIRouter()

# DeepSeek Reasoner API 配置（从环境变量读取）
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

async def _generate(req: Request):
    body        = await req.json()
    prompt      = body.get("inputs", "")
    max_tokens  = body.get("parameters", {}).get("max_new_tokens", 512)
    temperature = body.get("parameters", {}).get("temperature", 0.7)

    payload = {
        "model": "deepseek-reasoner",  # 使用DeepSeek R1模型的正确名称
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            text = result["choices"][0]["message"]["content"]
            if not text:  # 如果返回空内容，提供中文默认响应
                text = "我理解您的请求，但无法生成内容。"
            return {"generated_text": text.strip()}
    except Exception as e:
        print(f"Error calling DeepSeek Reasoner API: {e}")
        return {"generated_text": "抱歉，处理您的请求时遇到了错误。请检查DeepSeek API密钥和网络连接。"}

# 接 /generate
@router.post("/generate")
async def gen1(req: Request):
    return await _generate(req)

# 接 /generate/generate
@router.post("/generate/generate")
async def gen2(req: Request):
    return await _generate(req)

# 接 /
@router.post("/")
async def gen0(req: Request):
    return await _generate(req)

app.include_router(router, prefix="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)