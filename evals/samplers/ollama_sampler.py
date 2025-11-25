import time
from typing import Any
import os
import sys

# Add parent directory to path to import ollama_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ollama_client import get_ollama_client
from ..types import MessageList, SamplerBase, SamplerResponse

OLLAMA_SYSTEM_MESSAGE = "You are a helpful medical assistant."


class OllamaSampler(SamplerBase):
    """
    Sample from Ollama API (replacement for OpenAI sampler)
    """

    def __init__(
        self,
        model: str = "alibayram/medgemma:4b",
        system_message: str | None = None,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ):
        ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
        self.client = get_ollama_client(host=ollama_host, model=model)
        self.model = model
        self.system_message = system_message
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _handle_text(self, text: str):
        return {"type": "text", "text": text}

    def _pack_message(self, role: str, content: Any):
        return {"role": str(role), "content": content}

    def __call__(self, message_list: MessageList) -> SamplerResponse:
        if self.system_message:
            message_list = [
                self._pack_message("system", self.system_message)
            ] + message_list
        
        trial = 0
        max_trials = 3
        
        while trial < max_trials:
            try:
                response = self.client.chat_completions_create(
                    messages=message_list,
                    stream=False,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("Ollama API returned empty response; retrying")
                
                return SamplerResponse(
                    response_text=content,
                    response_metadata={"model": self.model},
                    actual_queried_message_list=message_list,
                )
            except Exception as e:
                exception_backoff = 2**trial  # exponential back off
                print(
                    f"Ollama exception, retrying {trial} after {exception_backoff} sec: {e}",
                )
                time.sleep(exception_backoff)
                trial += 1
        
        # If all retries fail, return error response
        return SamplerResponse(
            response_text="No response (Ollama failed after retries).",
            response_metadata={"model": self.model, "error": True},
            actual_queried_message_list=message_list,
        )

