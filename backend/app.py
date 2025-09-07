from fastapi import FastAPI, Query, Body, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import requests
import json
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import httpx
from litellm import acompletion

app = FastAPI()

# 👇 CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔥 Restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# In-memory session store
sessions = {}

@app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                return {"status": "ok", "ollama": "available"}
            else:
                return JSONResponse(
                    status_code=503,
                    content={"status": "error", "ollama": "unreachable"}
                )
    except httpx.RequestError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "ollama": "unreachable"}
        )

@app.get("/chat")
async def chat(
    prompt: str = Query(...),
    session_id: str = Query(...),
    model: str = Query(...)
):
    if session_id not in sessions:
        sessions[session_id] = []

    # Save user message
    sessions[session_id].append({"role": "user", "content": prompt})

    async def stream_response():
        accumulated_reply = ""

        try:
            params = {
                "model": f"ollama/{model}",                        # e.g., "llama3"
                "messages": sessions[session_id],
                "stream": True,
                "api_base": OLLAMA_URL                # 👈 always Ollama
            }

            # 🔑 Call LiteLLM async streaming API
            response = await acompletion(**params)

            async for chunk in response:
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                if not content:
                    content = chunk.get("completion")
                if content:
                    accumulated_reply += content
                    escaped = content.replace("\n", "\\n").replace("\r", "\\r")
                    yield f"data: {escaped}\n\n"

            # ✅ Save assistant reply after streaming finishes
            if accumulated_reply:
                sessions[session_id].append(
                    {"role": "assistant", "content": accumulated_reply}
                )


        except Exception as e:
            import traceback
            print("Exception:", traceback.format_exc())
            yield f"data: [error] {str(e)}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        }
    )


async def pull_model(model_name: str) -> dict:
    async with httpx.AsyncClient(timeout=None) as client:
        for attempt in range(10):
            try:
                print(f"📥 Pulling model attempt {attempt+1} for {model_name}")
                resp = await client.post(f"{OLLAMA_URL}/api/pull", json={"name": model_name})
                print(f"➡️ Pull response: {resp.status_code}, body: {resp.text}")
            except Exception as e:
                print(f"❌ Exception during model pull: {e}")

            # Wait before checking
            await asyncio.sleep(600)

            try:
                resp_tags = await client.get(f"{OLLAMA_URL}/api/tags")
                if resp_tags.status_code == 200:
                    models = resp_tags.json().get("models", [])
                    if any(m.get("name") == model_name for m in models):
                        print(f"✅ Model {model_name} is now available locally.")
                        return {"status": "ok", "model": model_name, "available": True}
            except Exception as e:
                print(f"❌ Exception during tag check: {e}")

        print(f"⚠️ Model {model_name} was not available after 10 attempts.")
        return {"status": "failed", "model": model_name, "available": False}


@app.post("/models/download")
async def download_model(request: Request):
    body = await request.json()
    model_name = body.get("model")
    if not model_name:
        return {"status": "error", "detail": "Missing 'model' in request body"}
    result = await pull_model(model_name)
    return result

@app.get("/models/list")
async def list_models():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return {"status": "ok", "models": data.get("models", [])}
            else:
                return JSONResponse(
                    status_code=503,
                    content={"error": "Unable to fetch models"}
                )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/models/delete")
async def delete_models(body: dict = Body(...)):
    models = body.get("models", [])
    if not models:
        raise HTTPException(status_code=400, detail="No models provided")

    deleted = []
    errors = []
    async with httpx.AsyncClient() as client:
        for model_name in models:
            try:
                resp = await client.request(
                    "DELETE",
                    f"{OLLAMA_URL}/api/delete",
                    content=json.dumps({"name": model_name}),
                    headers={"Content-Type": "application/json"}
                )
                if resp.status_code == 200:
                    deleted.append(model_name)
                else:
                    errors.append({"model": model_name, "error": resp.text})
            except Exception as e:
                errors.append({"model": model_name, "error": str(e)})

    return {"deleted": deleted, "errors": errors}


