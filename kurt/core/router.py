"""
KURT Router - Nag-cocall ng tamang AI API
Supports: OpenRouter, Groq, Google AI, DeepSeek, Ollama (local)
"""

from kurt.utils.security import redact

import os
import json
import asyncio
import httpx
from typing import Optional, AsyncGenerator


class ModelRouter:
    """Routes requests to the correct AI provider"""
    supports_native_tools = True

    def __init__(self):
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.google_key = os.getenv("GOOGLE_AI_KEY", "")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.fal_key = os.getenv("FAL_API_KEY", "")
        self.replicate_key = os.getenv("REPLICATE_API_TOKEN", "")

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
            "fal": self.fal_key,
            "replicate": self.replicate_key,
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
        stream: bool = True,
        native_tools: Optional[list] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """Call any model via OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "HTTP-Referer": "https://github.com/daddytito/kurt-ai",
            "X-Title": "KURT",
            "Content-Type": "application/json",
        }

        if native_tools:
            async for chunk in self._call_tool_chat(model, messages, stream, native_tools,
                                                    "https://openrouter.ai/api/v1/chat/completions", headers,
                                                    temperature=temperature):
                yield chunk
            return

        payload = {
            "model": model,
            "messages": redact(messages),
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature

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
        stream: bool = True,
        native_tools: Optional[list] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """Call models via Groq (super fast!)"""
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }
        async for chunk in self._call_tool_chat(model, messages, stream, native_tools,
                                                "https://api.groq.com/openai/v1/chat/completions", headers,
                                                temperature=temperature):
            yield chunk

    async def _call_tool_chat(self, model, messages, stream, native_tools, endpoint, headers, temperature=None):
        """Shared SSE function-call transport for compatible model providers."""

        payload = {
            "model": model,
            "messages": redact(messages),
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        yielded_any = False
        collected_text = ""
        calls = {}
        if native_tools:
            from kurt.capabilities.bridge import function_history
            payload["messages"] = function_history(redact(messages), native_tools)
            payload["tools"] = native_tools
            payload["tool_choice"] = "auto"
            payload["parallel_tool_calls"] = False
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                endpoint,
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
                        except json.JSONDecodeError:
                            continue
                        # Groq can send a mid-stream error event (e.g. the model
                        # internally attempted its own tool-call format, which the
                        # API rejects since no `tools` param was declared). That
                        # chunk has no "choices" key — previously this was silently
                        # swallowed by the KeyError catch below, making a rejected
                        # request look identical to "model returned nothing."
                        if "error" in chunk:
                            err = chunk["error"]
                            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                            raise RuntimeError(f"Model provider API error: {msg}")
                        try:
                            delta = chunk["choices"][0]["delta"]
                            if native_tools:
                                collected_text += delta.get("content") or ""
                                for call in delta.get("tool_calls", []):
                                    entry = calls.setdefault(call["index"], {"id": "", "name": "", "arguments": ""})
                                    entry["id"] += call.get("id") or ""
                                    entry["name"] += call.get("function", {}).get("name") or ""
                                    entry["arguments"] += call.get("function", {}).get("arguments") or ""
                                continue
                            if "content" in delta and delta["content"]:
                                yielded_any = True
                                yield delta["content"]
                        except (KeyError, IndexError):
                            continue
        if native_tools and calls:
            if len(calls) != 1:
                raise RuntimeError("Expected one native tool call per response.")
            call = next(iter(calls.values()))
            allowed_names = {t["function"]["name"] for t in native_tools}
            if call["name"] not in allowed_names:
                raise RuntimeError("Model provider returned an undeclared native tool.")
            try:
                arguments = json.loads(call["arguments"])
                if not isinstance(arguments, dict):
                    raise ValueError("Expected object arguments.")
            except ValueError as exc:
                raise RuntimeError("Model provider returned invalid native tool arguments.") from exc
            yield "```tool\n" + json.dumps({"tool": call["name"], "params": arguments, "call_id": call["id"]}) + "\n```"
            yielded_any = True
        elif native_tools and collected_text:
            yield collected_text
            yielded_any = True
        if not yielded_any:
            raise RuntimeError(
                f"Groq returned no content for model '{model}' — the stream ended with no "
                "text and no explicit error. This usually means the model's response was "
                "entirely internal reasoning with no final answer."
            )

    async def call_groq_transcription(
        self,
        file_path: str,
        model: str = "whisper-large-v3",
    ) -> AsyncGenerator[str, None]:
        """Transcribe an audio file via Groq's Whisper endpoint (not chat completions)."""
        headers = {"Authorization": f"Bearer {self.groq_key}"}
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        files = {"file": (os.path.basename(file_path), file_bytes)}
        data = {"model": model}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                data=data,
                files=files,
            )
            response.raise_for_status()
            result = response.json()
            yield result.get("text", "")

    async def call_fal(
        self,
        prompt: str,
        model: str = "fal-ai/flux/schnell",
    ) -> AsyncGenerator[str, None]:
        """Generate an image via fal.ai, yield the resulting image URL."""
        headers = {
            "Authorization": f"Key {self.fal_key}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": redact(prompt)}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"https://fal.run/{model}", headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    detail = response.json().get('detail', 'Request rejected')
                except (ValueError, AttributeError):
                    detail = 'Request rejected'
                raise RuntimeError(f"fal.ai HTTP {response.status_code}: {redact(str(detail))[:1000]}") from exc
            data = response.json()
            images = data.get("images", [])
            if not images:
                raise RuntimeError(f"fal.ai returned no images: {data}")
            yield images[0].get("url", "")

    async def call_replicate(
        self,
        model: str,
        input_params: dict,
    ) -> AsyncGenerator[str, None]:
        """Run a model on Replicate (blocks via Prefer: wait, polls if it runs long), yield the output URL."""
        headers = {
            "Authorization": f"Bearer {self.replicate_key}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }
        payload = {"input": redact(input_params)}

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Not every model (official or community) supports the
            # /v1/models/{owner}/{name}/predictions shorthand — look up the
            # latest version hash and create the prediction the universal way.
            model_resp = await client.get(f"https://api.replicate.com/v1/models/{model}", headers=headers)
            model_resp.raise_for_status()
            version_id = model_resp.json().get("latest_version", {}).get("id")
            if not version_id:
                raise RuntimeError(f"Replicate model '{model}' has no latest_version to run")

            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={"version": version_id, **payload},
            )
            response.raise_for_status()
            data = response.json()

            while data.get("status") in ("starting", "processing"):
                await asyncio.sleep(2)
                from urllib.parse import urlsplit
                poll_url = data["urls"]["get"]
                parsed = urlsplit(poll_url)
                if parsed.scheme != "https" or parsed.hostname != "api.replicate.com" or parsed.port not in (None, 443) or parsed.username or parsed.password:
                    raise ValueError("Refusing to send Replicate credentials to an untrusted polling origin")
                poll = await client.get(poll_url, headers=headers)
                poll.raise_for_status()
                data = poll.json()

            if data.get("status") != "succeeded":
                raise RuntimeError(f"Replicate prediction failed: {data.get('error') or data.get('status')}")

            output = data.get("output")
            if isinstance(output, list):
                output = output[0] if output else ""
            yield str(output)

    async def call_anthropic(
        self,
        model: str,
        messages: list,
        stream: bool = True,
        temperature: Optional[float] = None,
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
        for m in redact(messages):
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
        if temperature is not None:
            payload["temperature"] = temperature

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
        stream: bool = True,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """Call local models via Ollama (offline fallback!)"""
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        payload = {
            "model": model,
            "messages": redact(messages),
            "stream": stream,
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}

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

    # Replicate model name -> real owner/name slug on Replicate
    REPLICATE_MODEL_SLUGS = {
        "musicgen-large": "meta/musicgen",
        "wan-2.1": "wavespeedai/wan-2.1-t2v-480p",
    }
    GROQ_TRANSCRIPTION_MODELS = ("whisper-large-v3", "whisper-large-v3-turbo")

    async def route(
        self,
        provider: str,
        model: str,
        messages: list,
        stream: bool = True,
        file_path: Optional[str] = None,
        native_tools: Optional[list] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """Main routing function - picks the right provider"""

        messages = redact(messages)

        # Check if provider key exists, fallback to openrouter
        if not self._has_key(provider) and provider not in ("ollama",):
            # Try openrouter as universal fallback
            if self._has_key("openrouter"):
                provider = "openrouter"
            else:
                # Last resort: local ollama
                provider = "ollama"
                model = "llama3"

        if provider == "openrouter":
            async for chunk in self.call_openrouter(model, messages, stream, native_tools=native_tools, temperature=temperature):
                yield chunk
        elif provider == "anthropic":
            # Try direct Anthropic API, fallback to OpenRouter
            if self._has_key("anthropic"):
                async for chunk in self.call_anthropic(model, messages, stream, temperature=temperature):
                    yield chunk
            elif self._has_key("openrouter"):
                # Route Claude via OpenRouter
                or_model = model if "/" in model else f"anthropic/{model}"
                async for chunk in self.call_openrouter(or_model, messages, stream, native_tools=native_tools, temperature=temperature):
                    yield chunk
            else:
                raise RuntimeError("No Anthropic API key and no OpenRouter key — cannot call Claude!")
        elif provider == "groq":
            if model in self.GROQ_TRANSCRIPTION_MODELS:
                # Audio transcription — not a chat message, needs an actual file.
                path = file_path or (messages[-1]["content"] if messages else "")
                async for chunk in self.call_groq_transcription(path, model):
                    yield chunk
            else:
                groq_model = model.replace("groq/", "")
                async for chunk in self.call_groq(groq_model, messages, stream, native_tools=native_tools, temperature=temperature):
                    yield chunk
        elif provider == "fal":
            prompt = messages[-1]["content"] if messages else ""
            async for chunk in self.call_fal(prompt, model):
                yield chunk
        elif provider == "replicate":
            prompt = messages[-1]["content"] if messages else ""
            replicate_model = self.REPLICATE_MODEL_SLUGS.get(model, model)
            async for chunk in self.call_replicate(replicate_model, {"prompt": prompt}):
                yield chunk
        elif provider == "ollama":
            async for chunk in self.call_ollama(model, messages, stream, temperature=temperature):
                yield chunk
        else:
            # Default fallback: openrouter
            async for chunk in self.call_openrouter(model, messages, stream, native_tools=native_tools, temperature=temperature):
                yield chunk
