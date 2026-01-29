"""Cliente HTTP para Ollama API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

from ..config import get_config


@dataclass
class Message:
    """Mensaje de chat."""

    role: str  # system, user, assistant
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """Respuesta del LLM."""

    content: str
    done: bool = True
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None


class OllamaClient:
    """Cliente para API de Ollama."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int = 120,
    ) -> None:
        """Inicializar cliente."""
        config = get_config()
        self.host = host or config.ollama_host
        self.model = model or config.ollama_model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def check_connection(self) -> dict[str, Any]:
        """Verificar conexión con Ollama."""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_models(self) -> list[dict[str, Any]]:
        """Listar modelos disponibles."""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception:
            return []

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generar texto (modo no-streaming)."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        response = await self.client.post(
            f"{self.host}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("response", ""),
            done=data.get("done", True),
            total_duration=data.get("total_duration"),
            load_duration=data.get("load_duration"),
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
        )

    async def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generar texto en modo streaming."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with self.client.stream(
            "POST",
            f"{self.host}/api/generate",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                except json.JSONDecodeError:
                    continue

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Chat completion usando el endpoint generate."""
        # Convertir mensajes a formato de prompt
        system_messages = [m for m in messages if m.role == "system"]
        user_messages = [m for m in messages if m.role == "user"]
        
        system_prompt = system_messages[0].content if system_messages else ""
        user_prompt = user_messages[0].content if user_messages else ""
        
        # Combinar system y user en un solo prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
        else:
            full_prompt = user_prompt

        # Usar el método generate que sabemos que funciona
        return await self.generate(
            prompt=full_prompt,
            system=None,  # Ya está incluido en el prompt
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat_stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Chat completion en modo streaming."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with self.client.stream(
            "POST",
            f"{self.host}/api/chat",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    message = data.get("message", {})
                    if "content" in message:
                        yield message["content"]
                except json.JSONDecodeError:
                    continue

    async def close(self) -> None:
        """Cerrar cliente HTTP."""
        await self.client.aclose()
