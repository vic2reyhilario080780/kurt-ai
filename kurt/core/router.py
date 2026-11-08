"""
KURT Router - Nag-cocall ng tamang AI API
Supports: OpenRouter, Groq, Google AI, DeepSeek, Ollama (local)
"""

import os
import json
import httpx
from typing import Optional, AsyncGenerator


class ModelRouter:
    """Routes requests to the correct AI provider"""

    def __init__(self):
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.google_key = os.getenv("GOOGLE_AI_KEY", "")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    def _has_key(self, provider: str) -> bool:
        """Check if a real API key exists (not empty, not a placeholder)"""
        PLACEHOLDER_PREFIXES = (
            "sk-or-v1-your", "AIzaSy-your", "gsk_your", "sk-your",
            "sk-ant-your", "your-key", "r8_your", "placeholder",
        )
        keys = {
            "openrouter": self.openrouter_key,
            "groq": self.groq_key,
            "google": self.google_key,
            "deepseek": self.deepseek_key,
            "openai": self.openai_key,
            "anthropic": self.anthropic_key,
        }
        key = keys.get(provider, "")
        if not key:
            return False
        # Reject placeholder values from .env.example
        if any(key.startswith(p) for p in PLACEHOLDER_PREFIXES):
            return False
        return True

    async def call_openrouter(
        self,
        model: str,
        messages: list,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Call any model via OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "HTTP-Referer": "https://github.com/daddytito/kurt-ai",
            "X-Title": "KURT",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def call_groq(
        self,
        model: str,
        messages: list,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Call models via Groq (super fast!)"""
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def call_anthropic(
        self,
        model: str,
        messages: list,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Call Claude directly via Anthropic API (native, not via OpenRouter)"""
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Separate system messages from user/assistant messages
        system_parts = []
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                chat_messages.append(m)

        payload = {
            "model": model,
            "max_tokens": 8096,
            "stream": stream,
            "messages": chat_messages,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except (json.JSONDecodeError, KeyError):
                            continue

    async def call_ollama(
        self,
        model: str,
        messages: list,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Call local models via Ollama (offline fallback!)"""
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{ollama_host}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]
                            if chunk.get("done", False):
                                break
                        except (json.JSONDecodeError, KeyError):
                            continue

    async def route(
        self,
        provider: str,
        model: str,
        messages: list,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Main routing function - picks the right provider"""

        # Check if provider key exists, fallback to openrouter
        if not self._has_key(provider) and provider != "ollama":
            # Try openrouter as universal fallback
            if self._has_key("openrouter"):
                provider = "openrouter"
            else:
                # Last resort: local ollama
                provider = "ollama"
                model = "llama3"

        if provider == "openrouter":
            async for chunk in self.call_openrouter(model, messages, stream):
                yield chunk
        elif provider == "anthropic":
            # Try direct Anthropic API, fallback to OpenRouter
            if self._has_key("anthropic"):
                async for chunk in self.call_anthropic(model, messages, stream):
                    yield chunk
            elif self._has_key("openrouter"):
                # Route Claude via OpenRouter
                or_model = model if "/" in model else f"anthropic/{model}"
                async for chunk in self.call_openrouter(or_model, messages, stream):
                    yield chunk
            else:
                raise RuntimeError("No Anthropic API key and no OpenRouter key — cannot call Claude!")
        elif provider == "groq":
            # Map groq model names
            groq_model = model.replace("groq/", "")
            async for chunk in self.call_groq(groq_model, messages, stream):
                yield chunk
        elif provider == "ollama":
            async for chunk in self.call_ollama(model, messages, stream):
                yield chunk
        else:
            # Default fallback: openrouter
            async for chunk in self.call_openrouter(model, messages, stream):
                yield chunk
