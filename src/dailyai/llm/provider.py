"""
DailyAI — LLM Provider Layer
Uses LangChain's with_fallbacks() to cascade through providers.
Replaces 500+ lines of manual HTTP calls with ~80 lines.
"""

import logging
import os
from functools import lru_cache

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("dailyai.llm")


def _order_providers(providers: list[tuple[str, BaseChatModel]], *, prefer_gemini: bool) -> list[tuple[str, BaseChatModel]]:
    """Order providers by reliability/performance policy.

    Fast path policy requested by product: Gemini first, then other providers.
    Groq is kept as a late fallback due frequent free-tier 429s.
    """
    if prefer_gemini:
        priority = ["gemini", "arliai", "nvidia", "huggingface", "groq", "ollama"]
    else:
        priority = ["gemini", "arliai", "nvidia", "huggingface", "groq", "ollama"]

    rank = {name: i for i, name in enumerate(priority)}
    return sorted(providers, key=lambda p: rank.get(p[0], 999))


def _build_providers() -> list[tuple[str, BaseChatModel]]:
    """Build list of available LLM providers based on env vars."""
    providers: list[tuple[str, BaseChatModel]] = []

    # 1. ARLIAI (PRIMARY when configured; OpenAI-compatible endpoint)
    arliai_key = os.getenv("ARLIAI_API_KEY", "").strip()
    if arliai_key:
        try:
            from langchain_openai import ChatOpenAI

            arliai_base_url = os.getenv("ARLIAI_BASE_URL", "https://api.arliai.com/v1").strip().rstrip("/")
            if not arliai_base_url.endswith("/v1"):
                arliai_base_url = f"{arliai_base_url}/v1"

            arliai_model = os.getenv("ARLIAI_MODEL", "Qwen3.5-27B-Anko").strip() or "Qwen3.5-27B-Anko"

            providers.append((
                "arliai",
                ChatOpenAI(
                    base_url=arliai_base_url,
                    model=arliai_model,
                    api_key=arliai_key,
                    temperature=0.3,
                    max_tokens=4096,
                    max_retries=0,
                    timeout=12,
                ),
            ))
            logger.info(f"[LLM] ✅ ARLIAI provider configured ({arliai_model})")
        except Exception as e:
            logger.warning(f"[LLM] ARLIAI setup failed: {e}")

    # 2. Google Gemini (free, generous limits)
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
                    timeout=12,  # Gemini API enforces minimum >= 10s manual deadline
                ),
            ))
            logger.info("[LLM] ✅ Gemini provider configured")
        except Exception as e:
            logger.warning(f"[LLM] Gemini setup failed: {e}")

    # 3. Groq (fast, free tier)
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
                    timeout=8,
                ),
            ))
            logger.info("[LLM] ✅ Groq provider configured")
        except Exception as e:
            logger.warning(f"[LLM] Groq setup failed: {e}")

    # 4. NVIDIA (DeepSeek via OpenAI-compatible endpoint)
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
                    timeout=15,
                ),
            ))
            logger.info("[LLM] ✅ NVIDIA provider configured")
        except Exception as e:
            logger.warning(f"[LLM] NVIDIA setup failed: {e}")

    # 5. HuggingFace (free serverless)
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
                    max_retries=1,  # Allow one retry for cold start recovery
                    timeout=25,  # HF serverless needs 10-30s for cold starts
                ),
            ))
            logger.info("[LLM] ✅ HuggingFace provider configured")
        except Exception as e:
            logger.warning(f"[LLM] HuggingFace setup failed: {e}")

    # 6. Ollama (local, optional)
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
                    timeout=8,
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
    providers = _order_providers(_build_providers(), prefer_gemini=True)

    if not providers:
        raise RuntimeError(
            "No LLM providers configured! Set at least ARLIAI_API_KEY or GOOGLE_AI_KEY in .env"
        )

    primary_name, primary = providers[0]
    logger.info(f"[LLM] Primary provider: {primary_name}")

    if len(providers) > 1:
        fallback_models = [p[1] for p in providers[1:]]
        fallback_names = [p[0] for p in providers[1:]]
        logger.info(f"[LLM] Fallback chain: {' → '.join(fallback_names)}")
        return primary.with_fallbacks(fallback_models)

    return primary


@lru_cache(maxsize=1)
def get_fast_llm() -> BaseChatModel:
    """Get a fast LLM for brief generation.

    Gemini-first order for fastest stable UX. Groq is a late fallback due
    frequent free-tier 429 rate limits.
    """
    providers = _order_providers(_build_providers(), prefer_gemini=True)

    if not providers:
        raise RuntimeError("No LLM providers configured!")

    primary_name, primary = providers[0]
    logger.info(f"[LLM-fast] Primary provider: {primary_name}")

    if len(providers) > 1:
        fallback_models = [p[1] for p in providers[1:]]
        fallback_names = [p[0] for p in providers[1:]]
        logger.info(f"[LLM-fast] Fallback chain: {' → '.join(fallback_names)}")
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
    path = "fast" if fast else "main"
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
        logger.error(f"[LLM-{path}] All providers failed: {e}")
        return ""


async def warmup_hf_model() -> None:
    """Pre-warm HuggingFace serverless model to avoid cold start on first user request.

    Sends a tiny prompt so HF loads the model into memory.
    Fire-and-forget — failures are silently logged.
    """
    hf_token = os.getenv("HF_API_TOKEN", "")
    if not hf_token:
        return
    try:
        logger.info("[LLM] Warming up HuggingFace model...")
        payload = {
            "model": "mistralai/Mistral-Small-24B-Instruct-2501",
            "messages": [{"role": "user", "content": "Say OK"}],
            "max_tokens": 5,
            "temperature": 0.0,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {hf_token}",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://router.huggingface.co/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            if resp.status_code == 200:
                logger.info("[LLM] ✅ HuggingFace model warmed up successfully")
            else:
                logger.warning(f"[LLM] HF warmup got status {resp.status_code} (model may still be loading)")
    except Exception as e:
        logger.warning(f"[LLM] HF warmup failed (non-critical): {e}")
