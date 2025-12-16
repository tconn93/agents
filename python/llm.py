from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
import os
import warnings
import logging

# Each provider has its own library.
# You will need to install them:
# pip install openai anthropic google-generativeai groq
from openai import AsyncOpenAI
import anthropic
import google.generativeai as genai
from groq import AsyncGroq

logger = logging.getLogger(__name__)

class LLM(ABC):
    """
    Abstract Base Class for a Large Language Model provider.
    It defines the interface for interacting with different LLM APIs.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generates a chat completion response.

        Args:
            messages: A list of message dictionaries, e.g., [{"role": "user", "content": "Hello"}].
            temperature: The sampling temperature for the completion.
            max_tokens: The maximum number of tokens to generate.
            **kwargs: Additional provider-specific arguments.

        Returns:
            A dictionary representing the normalized response from the LLM.
        """
        pass


class OpenAIProvider(LLM):
    """LLM provider for OpenAI models."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise ValueError("OPENAI_API_KEY must be provided or set as an environment variable.")

        super().__init__(api_key=resolved_api_key, model=model)
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generates a chat completion response using the OpenAI API."""
        # Separate system prompt if present, as it's a top-level parameter for some models
        system_prompt = ""
        if messages and messages[0]['role'] == 'system':
            system_prompt = messages[0]['content']
            messages = messages[1:]

        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return completion.dict()

class Grok(LLM):
    """LLM provider for xAI (Grok) models, using an OpenAI-compatible API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "grok-4"):
        resolved_api_key = api_key or os.getenv("XAI_API_KEY")
        if not resolved_api_key:
            raise ValueError("XAI_API_KEY must be provided or set as an environment variable.")

        super().__init__(api_key=resolved_api_key, model=model)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generates a chat completion response using the xAI API."""
        logger.info(
            "Calling xAI API.",
            extra={"model": self.model, "temperature": temperature, "max_tokens": max_tokens}
        )
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        # Normalize the response to a standard dictionary format
        return completion.dict()


class GroqProvider(LLM):
    """LLM provider for Groq models."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama3-8b-8192"):
        resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_api_key:
            raise ValueError("GROQ_API_KEY must be provided or set as an environment variable.")

        super().__init__(api_key=resolved_api_key, model=model)
        self.client = AsyncGroq(api_key=self.api_key)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generates a chat completion response using the Groq API."""
        logger.info(
            "Calling Groq API.",
            extra={"model": self.model, "temperature": temperature, "max_tokens": max_tokens}
        )
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        # Normalize the response to a standard dictionary format
        return completion.dict()


class Claude(LLM):
    """LLM provider for Anthropic (Claude) models."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        resolved_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set as an environment variable.")

        super().__init__(api_key=resolved_api_key, model=model)
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generates a chat completion response using the Anthropic API."""
        system_prompt = ""
        if messages and messages[0]['role'] == 'system':
            system_prompt = messages[0]['content']
            messages = messages[1:]

        logger.info(
            "Calling Anthropic API.",
            extra={"model": self.model, "temperature": temperature, "max_tokens": max_tokens}
        )

        completion = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        # Normalize the response to a standard dictionary format
        return {
            "choices": [{"message": {"role": "assistant", "content": completion.content[0].text}}]
        }


class Gemini(LLM):
    """LLM provider for Google (Gemini) models."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        resolved_api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not resolved_api_key:
            raise ValueError("GOOGLE_API_KEY must be provided or set as an environment variable.")

        super().__init__(api_key=resolved_api_key, model=model)
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(
            model_name=self.model,
            # System instructions are handled differently in Gemini
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generates a chat completion response using the Google Gemini API."""
        # Gemini uses a different format for history and system prompts.
        # We adapt the standard message format to Gemini's format.
        system_prompt = None
        if messages and messages[0]['role'] == 'system':
            system_prompt = messages[0]['content']
            messages = messages[1:]

        # The Gemini API expects a specific format for conversation history.
        # We'll use a chat session for simplicity.
        chat = self.client.start_chat(history=[])
        if system_prompt:
            # Re-initialize the model with the system instruction
            self.client = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt
            )

        # The last message is the one we want a response for.
        user_prompt = messages[-1]['content']
        history = messages[:-1]

        # Gemini's `start_chat` history needs to be in its own format.
        # For this implementation, we'll just send the last prompt.
        # A more robust solution would convert the entire message history.
        if len(history) > 0:
            warnings.warn("Gemini provider in this implementation does not fully support history conversion yet. Only the last message will be sent.")

        logger.info(
            "Calling Gemini API.",
            extra={"model": self.model, "temperature": temperature, "max_tokens": max_tokens}
        )

        completion = await chat.send_message_async(
            user_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        # Normalize the response to a standard dictionary format
        return {
            "choices": [{"message": {"role": "assistant", "content": completion.text}}]
        }

# --- Provider Factory ---

PROVIDERS: Dict[str, Type[LLM]] = {
    "openai": OpenAIProvider,
    "xai": Grok,
    "groq": GroqProvider,
    "claude": Claude,
    "gemini": Gemini,
}

def get_llm(provider_name: str, **kwargs: Any) -> LLM:
    """Factory function to get an instance of an LLM provider."""
    provider_class = PROVIDERS.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown LLM provider: '{provider_name}'. Available: {list(PROVIDERS.keys())}")
    return provider_class(**kwargs)