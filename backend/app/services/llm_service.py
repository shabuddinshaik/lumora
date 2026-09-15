import requests


OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "qwen3:8b"


def generate_answer(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
        },
        timeout=300,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("response", "").strip()
