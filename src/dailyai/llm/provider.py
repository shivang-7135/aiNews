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
SUMMARY_FALLBACK_MESSAGE = (
    "Our AI models are experiencing high traffic right now. "
    "Please tap 'Read Original' to view the full story on the publisher's website."
)


def _order_providers(providers: list[tuple[str, BaseChatModel]]) -> list[tuple[str, BaseChatModel]]:
    """Order providers by reliability/performance policy.

    OpenAI gpt-4o-mini is preferred, then cloud fallbacks.
    Groq is kept as a late fallback due frequent free-tier 429s.
    """
    priority = ["openai", "gemini", "arliai", "nvidia", "huggingface", "groq", "ollama"]

    rank = {name: i for i, name in enumerate(priority)}
    return sorted(providers, key=lambda p: rank.get(p[0], 999))


def _build_providers() -> list[tuple[str, BaseChatModel]]:
    """Build list of available LLM providers based on env vars."""
    providers: list[tuple[str, BaseChatModel]] = []
    fallback_timeout = max(6.0, float(os.getenv("LLM_FALLBACK_TIMEOUT_SECONDS", "10")))

    # 0. OpenAI (PRIMARY)
    openai_key = (os.getenv("OPENAI_API_KEY", "") or os.getenv("OPENAI_KEY", "")).strip()
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI

            openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
            openai_timeout = max(10.0, float(os.getenv("OPENAI_TIMEOUT_SECONDS", "22")))

            providers.append(
                (
                    "openai",
                    ChatOpenAI(
                        model=openai_model,
                        api_key=openai_key,
                        temperature=0.3,
                        max_tokens=4090,
                        max_retries=0,
                        timeout=openai_timeout,
                    ),
                )
            )
            logger.info(f"[LLM] ✅ OpenAI provider configured ({openai_model})")
        except Exception as e:
            logger.warning(f"[LLM] OpenAI setup failed: {e}")

    # 1. ARLIAI (OpenAI-compatible endpoint)
    arliai_key = os.getenv("ARLIAI_API_KEY", "").strip()
    if arliai_key:
        try:
            from langchain_openai import ChatOpenAI

            arliai_base_url = (
                os.getenv("ARLIAI_BASE_URL", "https://api.arliai.com/v1").strip().rstrip("/")
            )
            if not arliai_base_url.endswith("/v1"):
                arliai_base_url = f"{arliai_base_url}/v1"

            arliai_model = (
                os.getenv("ARLIAI_MODEL", "Qwen3.5-27B-Anko").strip() or "Qwen3.5-27B-Anko"
            )

            providers.append(
                (
                    "arliai",
                    ChatOpenAI(
                        base_url=arliai_base_url,
                        model=arliai_model,
                        api_key=arliai_key,
                        temperature=0.3,
                        max_tokens=4096,
                        max_retries=0,
                        timeout=fallback_timeout,
                    ),
                )
            )
            logger.info(f"[LLM] ✅ ARLIAI provider configured ({arliai_model})")
        except Exception as e:
            logger.warning(f"[LLM] ARLIAI setup failed: {e}")

    # 2. Google Gemini (free, generous limits)
    google_key = os.getenv("GOOGLE_AI_KEY", "")
    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            providers.append(
                (
                    "gemini",
                    ChatGoogleGenerativeAI(
                        model="gemini-2.0-flash",
                        google_api_key=google_key,
                        temperature=0.3,
                        max_output_tokens=4096,
                        max_retries=0,  # Fail fast to trigger fallback
                        timeout=max(10.0, fallback_timeout),  # Gemini API requires >= 10s deadline
                    ),
                )
            )
            logger.info("[LLM] ✅ Gemini provider configured")
        except Exception as e:
            logger.warning(f"[LLM] Gemini setup failed: {e}")

    # 3. Groq (fast, free tier)
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            from langchain_groq import ChatGroq

            providers.append(
                (
                    "groq",
                    ChatGroq(
                        model="llama-3.3-70b-versatile",
                        api_key=groq_key,
                        temperature=0.3,
                        max_tokens=4096,
                        max_retries=0,
                        timeout=max(6.0, min(8.0, fallback_timeout)),
                    ),
                )
            )
            logger.info("[LLM] ✅ Groq provider configured")
        except Exception as e:
            logger.warning(f"[LLM] Groq setup failed: {e}")

    # 4. NVIDIA (DeepSeek via OpenAI-compatible endpoint)
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    if nvidia_key:
        try:
            from langchain_openai import ChatOpenAI

            providers.append(
                (
                    "nvidia",
                    ChatOpenAI(
                        base_url="https://integrate.api.nvidia.com/v1",
                        model="deepseek-ai/deepseek-v3.1",
                        api_key=nvidia_key,
                        temperature=0.3,
                        max_tokens=4096,
                        max_retries=0,
                        timeout=max(10.0, fallback_timeout + 2),
                    ),
                )
            )
            logger.info("[LLM] ✅ NVIDIA provider configured")
        except Exception as e:
            logger.warning(f"[LLM] NVIDIA setup failed: {e}")

    # 5. HuggingFace (free serverless)
    hf_token = os.getenv("HF_API_TOKEN", "")
    if hf_token:
        try:
            from langchain_openai import ChatOpenAI

            providers.append(
                (
                    "huggingface",
                    ChatOpenAI(
                        base_url="https://router.huggingface.co/v1",
                        model="mistralai/Mistral-Small-24B-Instruct-2501",
                        api_key=hf_token,
                        temperature=0.3,
                        max_tokens=2048,
                        max_retries=0,
                        timeout=max(10.0, fallback_timeout + 2),
                    ),
                )
            )
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
            providers.append(
                (
                    "ollama",
                    ChatOpenAI(
                        base_url=ollama_base,
                        model=model,
                        api_key="ollama",  # Ollama doesn't need a key
                        temperature=0.3,
                        max_tokens=2048,
                        max_retries=0,
                        timeout=max(6.0, min(8.0, fallback_timeout)),
                    ),
                )
            )
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
    providers = _order_providers(_build_providers())

    if not providers:
        raise RuntimeError(
            "No LLM providers configured! Set at least OPENAI_API_KEY, GOOGLE_AI_KEY, or ARLIAI_API_KEY in .env"
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

    OpenAI-first order for fastest stable UX. Groq is a late fallback due
    frequent free-tier 429 rate limits.
    """
    providers = _order_providers(_build_providers())

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


async def stream_llm(
    system_prompt: str,
    user_prompt: str,
    fast: bool = False,
):
    """Invoke the LLM with system + user messages and stream the response back.

    Args:
        system_prompt: The system instruction.
        user_prompt: The user query.
        fast: If True, use the fast LLM path (for briefs).

    Yields:
        String chunks of the LLM response as they are generated.
    """
    import asyncio

    def _to_text(value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "".join(str(v) for v in value)
        return str(value or "")

    path = "fast" if fast else "main"
    llm = get_fast_llm() if fast else get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    streamed_any = False

    try:
        async for chunk in llm.astream(messages):
            text = _to_text(chunk.content if hasattr(chunk, "content") else chunk)
            if not text:
                continue
            streamed_any = True
            yield text
        if streamed_any:
            return
    except Exception as stream_error:
        logger.warning(
            f"[{path.capitalize()}-stream] Streaming failed, trying non-stream invoke: {stream_error}"
        )
        if streamed_any:
            return

    try:
        response = await llm.ainvoke(messages)
        text = _to_text(response.content if hasattr(response, "content") else response).strip()
        if text:
            chunk_size = max(60, min(220, len(text) // 10 if len(text) > 0 else 120))
            for i in range(0, len(text), chunk_size):
                yield text[i : i + chunk_size]
                await asyncio.sleep(0)
            return
    except Exception as invoke_error:
        logger.error(f"[{path.capitalize()}-stream] Non-stream invoke failed: {invoke_error}")

    yield SUMMARY_FALLBACK_MESSAGE


async def warmup_hf_model() -> None:
    """Pre-warm HuggingFace serverless model to avoid cold start on first user request.

    Sends a tiny prompt so HF loads the model into memory.
    Fire-and-forget — failures are silently logged.
    """
    if os.getenv("HF_WARMUP_ENABLED", "false").lower() != "true":
        return

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
                logger.info(f"[LLM] HF warmup skipped (status {resp.status_code})")
    except Exception as e:
        logger.warning(f"[LLM] HF warmup failed (non-critical): {e}")
