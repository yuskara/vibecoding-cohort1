#sudo apt update
#sudo apt install nodejs npm from typing import Iterator
from llm import client


class Asistan:
    def __init__(self, system_instructions: str, model: str = "qwen2.5-coder:3b"):
        self.model = model
        self.history: list[dict] = [
            {"role": "system", "content": system_instructions}
        ]

    def sohbet(self, user_prompt: str) -> str:
        self.history.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=self.history,
        )

        assistant_message = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    def stream_sohbet(self, user_prompt: str) -> Iterator[str]:
        self.history.append({"role": "user", "content": user_prompt})

        stream = client.chat.completions.create(
            model=self.model,
            messages=self.history,
            stream=True,
        )

        full_response = []
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_response.append(content)
                yield content

        self.history.append({"role": "assistant", "content": "".join(full_response)})
