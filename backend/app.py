from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
import requests
import json
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# 👇 CORS config goes here BEFORE defining your routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔥 Use ["http://localhost:3000"] in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


@app.get("/health")
def health_check():
    try:
        # /api/tags returns list of pulled models
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            return {"status": "ok", "ollama": "available"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "ollama": "unreachable"}
            )
    except requests.exceptions.RequestException:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "ollama": "unreachable"}
        )


@app.get("/chat")
def chat(prompt: str):
    def ollama_stream():
        print(f'prompt: {prompt}')
        payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": True
        }
        headers = {"Content-Type": "application/json"}

        with requests.post(f"{OLLAMA_URL}/api/generate", json=payload, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    try:
                        parsed = json.loads(line.decode("utf-8"))
                        content = parsed.get("response", "")
                        content = content.replace('\n', '\\n')
                        # ✅ Yield SSE-compliant event format
                        print(f"data: {content}\n\n")
                        yield f"data: {content}\n\n"
                    except Exception as e:
                        yield f"data: [error] {str(e)}\n\n"

    return StreamingResponse(ollama_stream(), media_type="text/event-stream")


