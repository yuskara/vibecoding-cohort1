import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import Iterator

load_dotenv()

OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE")
client_kwargs = {"base_url": OLLAMA_API_BASE}
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    client_kwargs["api_key"] = api_key
else:
    # When using local Ollama, provide a dummy API key since OpenAI client requires it
    client_kwargs["api_key"] = "not-needed"

client = OpenAI(**client_kwargs)


def stream_llm(
    system_instructions: str,
    user_prompt: str,
    model: str = "llama2",
) -> Iterator[str]:
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )

    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
