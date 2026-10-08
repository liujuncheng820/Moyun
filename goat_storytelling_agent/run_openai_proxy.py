import os

from fastapi import FastAPI, Request, APIRouter
import httpx

app   = FastAPI()
router = APIRouter()

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_URL = os.environ.get("OPENAI_BASE_URL", "https://free.v36.cm/v1/chat/completions")

async def _generate(req: Request):
    body        = await req.json()
    prompt      = body.get("inputs", "")
    max_tokens  = body.get("parameters", {}).get("max_new_tokens", 512)
    temperature = body.get("parameters", {}).get("temperature", 0.7)

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(OPENAI_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
    return {"generated_text": text.strip()}

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