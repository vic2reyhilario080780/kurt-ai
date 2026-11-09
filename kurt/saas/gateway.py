"""Provider key custody: only this control-plane client authenticates upstream."""
import json
import httpx
from .protocol import MAX_OUTPUT, scrub

MODELS = {"openai/gpt-oss-20b", "llama-3.3-70b-versatile"}


class ProviderUnavailable(RuntimeError):
    pass


class GroqGateway:
    def __init__(self, key, model="openai/gpt-oss-20b"):
        if not key or model not in MODELS:
            raise ValueError("A server-side Groq key and an approved model are required")
        self._key, self.model = key, model

    async def chat(self, messages):
        # No native tools, callback URL, tenant header, arbitrary provider URL,
        # files or desktop state are accepted from client requests.
        payload = {"model": self.model, "messages": scrub(messages, (self._key,)),
                   "max_tokens": 1024, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=45, follow_redirects=False, trust_env=False) as client:
                async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": "Bearer " + self._key}, json=payload) as response:
                    response.raise_for_status()
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > MAX_OUTPUT:
                            raise ProviderUnavailable("Provider response exceeded limit")
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Invalid provider content")
            return {"model": self.model, "content": scrub(content, (self._key,))}
        except Exception:
            # Provider exceptions/response bodies can include credentials/data.
            raise ProviderUnavailable("Provider request failed") from None
