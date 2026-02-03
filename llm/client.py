"""Multi-provider LLM client with fallback support"""

import asyncio
import json
from typing import Optional, List
from enum import Enum

from core.exceptions import LLMError
from core.enums import LLMProvider
from config import settings

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    # Fallback to deprecated package for backward compatibility
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False


class LLMClient:
    """Multi-provider LLM client with automatic fallback"""
    
    def __init__(self):
        self.providers = self._initialize_providers()
        self.provider_priority = settings.get_llm_provider_priority()
        self.max_retries = settings.LLM_MAX_RETRIES
        self.retry_delay = settings.LLM_RETRY_DELAY
        self.timeout = settings.LLM_TIMEOUT
        
    def _initialize_providers(self) -> dict:
        """Initialize available LLM providers"""
        providers = {}
        
        # Anthropic
        if ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            try:
                providers[LLMProvider.ANTHROPIC] = anthropic.Anthropic(
                    api_key=settings.ANTHROPIC_API_KEY,
                    timeout=settings.LLM_TIMEOUT
                )
            except Exception:
                pass
        
        # OpenAI
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                providers[LLMProvider.OPENAI] = openai.OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    timeout=settings.LLM_TIMEOUT
                )
            except Exception:
                pass
        
        # Gemini (using GOOGLE_API_KEY)
        if GEMINI_AVAILABLE and settings.GOOGLE_API_KEY:
            try:
                # Try new google.genai API first
                if hasattr(genai, 'Client'):
                    # New API: google.genai
                    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                    providers[LLMProvider.GEMINI] = client
                else:
                    # Old API: google.generativeai
                    genai.configure(api_key=settings.GOOGLE_API_KEY)
                    providers[LLMProvider.GEMINI] = genai
            except Exception:
                pass
        
        if not providers:
            raise LLMError(
                "No LLM providers available. "
                "Please configure at least one API key."
            )
        
        return providers
    
    def _get_available_providers(self) -> List[LLMProvider]:
        """Get list of available providers in priority order"""
        available = []
        for provider_name in self.provider_priority:
            try:
                provider = LLMProvider(provider_name)
                if provider in self.providers:
                    available.append(provider)
            except ValueError:
                continue
        return available
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0
    ) -> str:
        """
        Send completion request with automatic fallback
        
        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Response text
            
        Raises:
            LLMError: If all providers fail
        """
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        available_providers = self._get_available_providers()
        
        if not available_providers:
            raise LLMError("No available LLM providers")
        
        last_error = None
        
        # Try each provider in priority order
        for provider in available_providers:
            for attempt in range(self.max_retries):
                try:
                    response = await self._call_provider(
                        provider=provider,
                        prompt=prompt,
                        system=system,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    return response
                    
                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
            
            # If this provider failed all retries, try next provider
            continue
        
        # All providers failed
        raise LLMError(
            f"All LLM providers failed. Last error: {last_error}",
            provider=str(available_providers[-1]) if available_providers else None,
            retries=self.max_retries
        )
    
    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call specific LLM provider"""
        
        if provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(
                prompt, system, max_tokens, temperature
            )
        elif provider == LLMProvider.OPENAI:
            return await self._call_openai(
                prompt, system, max_tokens, temperature
            )
        elif provider == LLMProvider.GEMINI:
            return await self._call_gemini(
                prompt, system, max_tokens, temperature
            )
        else:
            raise LLMError(f"Unknown provider: {provider}")
    
    async def _call_anthropic(
        self,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call Anthropic Claude API"""
        client = self.providers[LLMProvider.ANTHROPIC]
        
        system_prompt = system or self._default_system_prompt()
        
        # Run in executor to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
        )
        
        return response.content[0].text
    
    async def _call_openai(
        self,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call OpenAI API"""
        client = self.providers[LLMProvider.OPENAI]
        
        system_prompt = system or self._default_system_prompt()
        
        # Run in executor to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
        )
        
        return response.choices[0].message.content
    
    async def _call_gemini(
        self,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call Google Gemini API - supports both new google.genai and old google.generativeai"""
        genai_client = self.providers[LLMProvider.GEMINI]
        
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        
        # Run in executor to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Try primary model, fallback to fallback model if configured
        model_id = settings.GEMINI_MODEL_ID or settings.GEMINI_FALLBACK_MODEL_ID or "gemini-2.5-pro"
        
        try:
            # Check if using new google.genai API (has Client) or old google.generativeai API
            if hasattr(genai_client, 'models') and hasattr(genai_client.models, 'generate_content'):
                # New API: google.genai
                response = await loop.run_in_executor(
                    None,
                    lambda: genai_client.models.generate_content(
                        model=model_id,
                        contents=full_prompt,
                        config={
                            "max_output_tokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                )
                return response.text
            else:
                # Old API: google.generativeai
                model = genai_client.GenerativeModel(model_id)
                response = await loop.run_in_executor(
                    None,
                    lambda: model.generate_content(
                        full_prompt,
                        generation_config=genai_client.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature
                        )
                    )
                )
                return response.text
        except Exception as e:
            # If primary model fails and fallback is configured, try fallback
            if settings.GEMINI_FALLBACK_MODEL_ID and model_id != settings.GEMINI_FALLBACK_MODEL_ID:
                fallback_id = settings.GEMINI_FALLBACK_MODEL_ID
                if hasattr(genai_client, 'models') and hasattr(genai_client.models, 'generate_content'):
                    # New API: google.genai
                    response = await loop.run_in_executor(
                        None,
                        lambda: genai_client.models.generate_content(
                            model=fallback_id,
                            contents=full_prompt,
                            config={
                                "max_output_tokens": max_tokens,
                                "temperature": temperature
                            }
                        )
                    )
                    return response.text
                else:
                    # Old API: google.generativeai
                    model = genai_client.GenerativeModel(fallback_id)
                    response = await loop.run_in_executor(
                        None,
                        lambda: model.generate_content(
                            full_prompt,
                            generation_config=genai_client.types.GenerationConfig(
                                max_output_tokens=max_tokens,
                                temperature=temperature
                            )
                        )
                    )
                    return response.text
            raise
    
    def _default_system_prompt(self) -> str:
        """Default system prompt for LLM tasks"""
        return (
            "You are a data analysis expert. "
            "Respond only with valid JSON when requested. "
            "No explanations or markdown unless specifically asked."
        )

