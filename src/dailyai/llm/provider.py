"""
DailyAI — LLM Provider Layer
Uses LangChain's with_fallbacks() to cascade through providers.
Replaces 500+ lines of manual HTTP calls with ~80 lines.
"""

import logging
import os
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("dailyai.llm")


def _build_providers() -> list[tuple[str, BaseChatModel]]:
    """Build list of available LLM providers based on env vars."""
    providers: list[tuple[str, BaseChatModel]] = []

    # 1. Google Gemini (PRIMARY — free, generous limits)
    google_key = os.getenv("GOOGLE_AI_KEY", "")
    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            providers.append((
                "gemini",
                ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=google_key,
                    temperature=0.3,
                    max_output_tokens=4096,
                    max_retries=0,  # Fail fast to trigger fallback
                ),
            ))
            logger.info("[LLM] ✅ Gemini provider configured")
        except Exception as e:
            logger.warning(f"[LLM] Gemini setup failed: {e}")

    # 2. Groq (fast, free tier)
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            from langchain_groq import ChatGroq

            providers.append((
                "groq",
                ChatGroq(
                    model="llama-3.3-70b-versatile",
                    api_key=groq_key,
                    temperature=0.3,
                    max_tokens=4096,
                    max_retries=0,
                ),
            ))
            logger.info("[LLM] ✅ Groq provider configured")
        except Exception as e:
            logger.warning(f"[LLM] Groq setup failed: {e}")

    # 3. NVIDIA (DeepSeek via OpenAI-compatible endpoint)
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    if nvidia_key:
        try:
            from langchain_openai import ChatOpenAI

            providers.append((
                "nvidia",
                ChatOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    model="deepseek-ai/deepseek-v3.1",
                    api_key=nvidia_key,
                    temperature=0.3,
                    max_tokens=4096,
                    max_retries=0,
                ),
            ))
            logger.info("[LLM] ✅ NVIDIA provider configured")
        except Exception as e:
            logger.warning(f"[LLM] NVIDIA setup failed: {e}")

    # 4. HuggingFace (free serverless)
    hf_token = os.getenv("HF_API_TOKEN", "")
    if hf_token:
        try:
            from langchain_openai import ChatOpenAI

            providers.append((
                "huggingface",
                ChatOpenAI(
                    base_url="https://router.huggingface.co/v1",
                    model="mistralai/Mistral-Small-24B-Instruct-2501",
                    api_key=hf_token,
                    temperature=0.3,
                    max_tokens=2048,
                    max_retries=0,
                ),
            ))
            logger.info("[LLM] ✅ HuggingFace provider configured")
        except Exception as e:
            logger.warning(f"[LLM] HuggingFace setup failed: {e}")

    # 5. Ollama (local, optional)
    ollama_base = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
    if ollama_base:
        try:
            from langchain_openai import ChatOpenAI

            if not ollama_base.endswith("/v1"):
                ollama_base = f"{ollama_base}/v1"
            model = os.getenv("OLLAMA_MODELS", "llama3.1:8b").split(",")[0].strip()
            providers.append((
                "ollama",
                ChatOpenAI(
                    base_url=ollama_base,
                    model=model,
                    api_key="ollama",  # Ollama doesn't need a key
                    temperature=0.3,
                    max_tokens=2048,
                    max_retries=0,
                ),
            ))
            logger.info(f"[LLM] ✅ Ollama provider configured ({model})")
        except Exception as e:
            logger.warning(f"[LLM] Ollama setup failed: {e}")

    return providers


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Get the primary LLM with fallback chain.

    Returns the first available provider with all others as fallbacks.
    Uses LangChain's with_fallbacks() for automatic cascading.
    """
    providers = _build_providers()

    if not providers:
        raise RuntimeError(
            "No LLM providers configured! Set at least GOOGLE_AI_KEY in .env"
        )

    primary_name, primary = providers[0]
    logger.info(f"[LLM] Primary provider: {primary_name}")

    if len(providers) > 1:
        fallback_models = [p[1] for p in providers[1:]]
        fallback_names = [p[0] for p in providers[1:]]
        logger.info(f"[LLM] Fallback chain: {' → '.join(fallback_names)}")
        return primary.with_fallbacks(fallback_models)

    return primary


def get_fast_llm() -> BaseChatModel:
    """Get a fast LLM for brief generation.

    Prioritizes speed: Groq → Gemini → others.
    """
    providers = _build_providers()

    # Reorder: prioritize Groq for speed
    groq_providers = [p for p in providers if p[0] == "groq"]
    other_providers = [p for p in providers if p[0] != "groq"]
    ordered = groq_providers + other_providers

    if not ordered:
        raise RuntimeError("No LLM providers configured!")

    primary_name, primary = ordered[0]

    if len(ordered) > 1:
        fallback_models = [p[1] for p in ordered[1:]]
        return primary.with_fallbacks(fallback_models)

    return primary


async def invoke_llm(
    system_prompt: str,
    user_prompt: str,
    fast: bool = False,
) -> str:
    """Invoke the LLM with system + user messages.

    Args:
        system_prompt: The system instruction.
        user_prompt: The user query.
        fast: If True, use the fast LLM path (for briefs).

    Returns:
        The LLM response text, or empty string on failure.
    """
    try:
        llm = get_fast_llm() if fast else get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        return content if isinstance(content, str) else str(content)
    except Exception as e:
        logger.error(f"[LLM] All providers failed: {e}")
        return ""
