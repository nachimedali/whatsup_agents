"""
LLM Provider Abstraction Layer
===============================
Normalises Anthropic, OpenAI (ChatGPT), and Google (Gemini) behind a single
async interface so the invoker loop doesn't care which provider is used.

Each provider handles:
  - System prompt injection (different conventions per SDK)
  - Tool call / tool result formatting (completely different schemas)
  - Response parsing back to plain text + tool call list

Usage:
    from services.llm import get_provider, MODELS_CATALOGUE

    provider = get_provider("anthropic")
    reply, tool_calls = await provider.complete(model, system, messages, tools)
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Any


# ── Models catalogue ─────────────────────────────────────────────────────────
# This is what the frontend reads to build its dropdowns.
# Structure: { provider_id: { label, models: [{id, label}] } }

MODELS_CATALOGUE: dict[str, dict] = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "models": [
            {"id": "claude-opus-4-6",              "label": "Claude Opus 4.6"},
            {"id": "claude-sonnet-4-6",             "label": "Claude Sonnet 4.6"},
            {"id": "claude-haiku-4-5-20251001",     "label": "Claude Haiku 4.5"},
            {"id": "claude-opus-4-5",               "label": "Claude Opus 4.5"},
            {"id": "claude-sonnet-4-5",             "label": "Claude Sonnet 4.5"},
            {"id": "claude-haiku-4-5",              "label": "Claude Haiku 4.5 (alt)"},
            {"id": "claude-3-7-sonnet-20250219",    "label": "Claude 3.7 Sonnet"},
            {"id": "claude-3-5-sonnet-20241022",    "label": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022",     "label": "Claude 3.5 Haiku"},
            {"id": "claude-3-opus-20240229",        "label": "Claude 3 Opus"},
        ],
    },
    "openai": {
        "label": "OpenAI (ChatGPT)",
        "models": [
            {"id": "gpt-4o",                        "label": "GPT-4o"},
            {"id": "gpt-4o-mini",                   "label": "GPT-4o Mini"},
            {"id": "gpt-4-turbo",                   "label": "GPT-4 Turbo"},
            {"id": "gpt-4",                         "label": "GPT-4"},
            {"id": "gpt-3.5-turbo",                 "label": "GPT-3.5 Turbo"},
            {"id": "o1",                            "label": "o1"},
            {"id": "o1-mini",                       "label": "o1 Mini"},
            {"id": "o3-mini",                       "label": "o3 Mini"},
        ],
    },
    "google": {
        "label": "Google (Gemini)",
        "models": [
            {"id": "gemini-2.0-flash",              "label": "Gemini 2.0 Flash"},
            {"id": "gemini-2.0-flash-lite",         "label": "Gemini 2.0 Flash Lite"},
            {"id": "gemini-1.5-pro",                "label": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash",              "label": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-flash-8b",           "label": "Gemini 1.5 Flash 8B"},
        ],
    },
}


# ── Normalised types ──────────────────────────────────────────────────────────

class ToolCall:
    """Normalised tool call returned by any provider."""
    def __init__(self, call_id: str, name: str, arguments: dict):
        self.call_id = call_id
        self.name = name
        self.arguments = arguments


class CompletionResult:
    """Normalised completion result."""
    def __init__(self, text: str, tool_calls: list[ToolCall], raw: Any = None):
        self.text = text
        self.tool_calls = tool_calls
        self.raw = raw   # provider-specific raw response, carried for multi-turn


# ── Abstract base ─────────────────────────────────────────────────────────────

class LLMProvider(ABC):
    """
    Abstract provider. Each subclass handles one SDK.

    Messages format (normalised, matches Anthropic's convention):
        [
          {"role": "user",      "content": "Hello"},
          {"role": "assistant", "content": "Hi!"},
          ...
        ]
    For tool results, content is a list of tool_result blocks (Anthropic-style).
    Each provider translates this to its own format internally.

    Tools format (Anthropic-style JSON schema dicts):
        [{"name": "...", "description": "...", "input_schema": {...}}, ...]
    Each provider translates these internally.
    """

    @abstractmethod
    async def complete(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> CompletionResult:
        ...

    @abstractmethod
    def append_assistant_turn(
        self,
        messages: list[dict],
        result: CompletionResult,
    ) -> list[dict]:
        """Append the assistant turn to the messages list for the next round."""
        ...

    @abstractmethod
    def append_tool_results(
        self,
        messages: list[dict],
        tool_calls: list[ToolCall],
        results: list[str],
    ) -> list[dict]:
        """Append tool results to messages for the next round."""
        ...


# ── Anthropic ─────────────────────────────────────────────────────────────────

class AnthropicProvider(LLMProvider):
    def __init__(self):
        import anthropic as _anthropic
        self._client = _anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

    async def complete(self, model, system, messages, tools) -> CompletionResult:
        kwargs: dict = dict(
            model=model,
            system=system,
            messages=messages,
            max_tokens=4096,
        )
        if tools:
            kwargs["tools"] = tools

        resp = await self._client.messages.create(**kwargs)

        text_parts = [b.text for b in resp.content if b.type == "text"]
        tool_calls = [
            ToolCall(b.id, b.name, b.input if isinstance(b.input, dict) else {})
            for b in resp.content if b.type == "tool_use"
        ]
        return CompletionResult(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            raw=resp.content,   # raw content blocks for appending
        )

    def append_assistant_turn(self, messages, result) -> list[dict]:
        return messages + [{"role": "assistant", "content": result.raw}]

    def append_tool_results(self, messages, tool_calls, results) -> list[dict]:
        blocks = [
            {"type": "tool_result", "tool_use_id": tc.call_id, "content": r}
            for tc, r in zip(tool_calls, results)
        ]
        return messages + [{"role": "user", "content": blocks}]


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    def _to_openai_tools(self, tools: list[dict]) -> list[dict]:
        """Convert Anthropic-style tool defs to OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    def _to_openai_messages(self, system: str, messages: list[dict]) -> list[dict]:
        """Prepend system message and pass through (OpenAI uses role=system in messages)."""
        out = [{"role": "system", "content": system}]
        for m in messages:
            if isinstance(m.get("content"), list):
                # tool_result blocks — already in OpenAI format if we built them correctly
                out.append(m)
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    async def complete(self, model, system, messages, tools) -> CompletionResult:
        oai_messages = self._to_openai_messages(system, messages)
        kwargs: dict = dict(model=model, messages=oai_messages)
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        resp = await self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        text = msg.content or ""
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_calls.append(ToolCall(tc.id, tc.function.name, args))

        return CompletionResult(text=text, tool_calls=tool_calls, raw=msg)

    def append_assistant_turn(self, messages, result) -> list[dict]:
        msg = result.raw
        # Rebuild as a plain dict for our normalised messages list
        entry: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return messages + [entry]

    def append_tool_results(self, messages, tool_calls, results) -> list[dict]:
        new = list(messages)
        for tc, r in zip(tool_calls, results):
            new.append({
                "role": "tool",
                "tool_call_id": tc.call_id,
                "content": r,
            })
        return new


# ── Google Gemini ─────────────────────────────────────────────────────────────

class GoogleProvider(LLMProvider):
    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
        self._genai = genai

    def _to_gemini_tools(self, tools: list[dict]):
        """Convert Anthropic-style tool defs to Gemini FunctionDeclaration format."""
        from google.generativeai.types import FunctionDeclaration, Tool as GeminiTool
        declarations = []
        for t in tools:
            schema = t.get("input_schema", {})
            declarations.append(FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=schema,
            ))
        return [GeminiTool(function_declarations=declarations)]

    def _to_gemini_history(self, messages: list[dict]) -> list[dict]:
        """
        Convert our normalised messages to Gemini's Content format.
        Gemini uses 'user'/'model' roles and parts=[{"text": "..."}].
        """
        history = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            content = m.get("content", "")
            if isinstance(content, str):
                history.append({"role": role, "parts": [{"text": content}]})
            elif isinstance(content, list):
                # tool results — encode as text for simplicity
                parts = []
                for block in content:
                    if block.get("type") == "tool_result":
                        parts.append({"text": f"[Tool result]: {block.get('content', '')}"})
                if parts:
                    history.append({"role": "user", "parts": parts})
        return history

    async def complete(self, model, system, messages, tools) -> CompletionResult:
        import google.generativeai as genai

        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            tools=self._to_gemini_tools(tools) if tools else None,
        )

        history = self._to_gemini_history(messages[:-1])  # all but last
        last_message = messages[-1]["content"] if messages else ""

        chat = gemini_model.start_chat(history=history)

        # Gemini SDK is synchronous — run in thread
        response = await asyncio.to_thread(chat.send_message, last_message)

        text = ""
        tool_calls = []

        for part in response.parts:
            if hasattr(part, "text") and part.text:
                text += part.text
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    call_id=fc.name,   # Gemini has no separate call ID
                    name=fc.name,
                    arguments=dict(fc.args),
                ))

        return CompletionResult(text=text.strip(), tool_calls=tool_calls, raw=response)

    def append_assistant_turn(self, messages, result) -> list[dict]:
        # For Gemini, we just add the text response as assistant
        return messages + [{"role": "assistant", "content": result.text}]

    def append_tool_results(self, messages, tool_calls, results) -> list[dict]:
        # Encode tool results as text blocks for Gemini
        blocks = [
            {"type": "tool_result", "tool_use_id": tc.call_id, "content": r}
            for tc, r in zip(tool_calls, results)
        ]
        return messages + [{"role": "user", "content": blocks}]


# ── Factory ───────────────────────────────────────────────────────────────────

_providers: dict[str, LLMProvider] = {}


def get_provider(provider_name: str) -> LLMProvider:
    """Return a cached provider instance. Raises ValueError for unknown providers."""
    if provider_name not in _providers:
        if provider_name == "anthropic":
            _providers[provider_name] = AnthropicProvider()
        elif provider_name == "openai":
            _providers[provider_name] = OpenAIProvider()
        elif provider_name == "google":
            _providers[provider_name] = GoogleProvider()
        else:
            raise ValueError(f"Unknown provider: '{provider_name}'. Use anthropic, openai, or google.")
    return _providers[provider_name]
