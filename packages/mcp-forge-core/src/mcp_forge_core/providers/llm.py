"""LLM provider base class for mcp-forge.

Defines the interface for language model invocations.
Subclass BaseLLMProvider and implement invoke() to create a custom backend.

Example::

    class MyLLMProvider(BaseLLMProvider):
        async def invoke(self, system_prompt, messages, *, max_tokens=4096, temperature=0.0):
            # call your LLM here
            return LLMResponse(text="hello", input_tokens=10, output_tokens=5, model="my-model")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """A single message in a conversation.

    Attributes:
        role: Either "user" or "assistant".
        content: Plain text string, or a list of multimodal content blocks
                 (e.g. [{"type": "text", "text": "..."}, {"type": "image", ...}]).
    """

    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Response from a language model invocation.

    Attributes:
        text: The generated text.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        model: The model identifier that produced this response.
    """

    text: str
    input_tokens: int
    output_tokens: int
    model: str


class BaseLLMProvider(ABC):
    """Base class for LLM backends.

    Subclass and implement :meth:`invoke` to integrate any language model.
    Similar to Django's BaseCache — swap implementations without changing tool code.

    Example::

        class OpenAIProvider(BaseLLMProvider):
            async def invoke(self, system_prompt, messages, *, max_tokens=4096, temperature=0.0):
                response = await openai_client.chat(...)
                return LLMResponse(...)
    """

    @abstractmethod
    async def invoke(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Invoke the language model with a system prompt and conversation messages.

        Args:
            system_prompt: Instructions for the model's behavior.
            messages: Ordered list of conversation messages.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            LLMResponse with generated text and token usage.
        """
        ...
