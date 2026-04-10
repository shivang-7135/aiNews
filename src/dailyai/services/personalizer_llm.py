import json
import logging
from datetime import UTC, datetime

from dailyai.llm.prompts import BESPOKE_PROMPT
from dailyai.llm.provider import invoke_llm
from dailyai.services.profiles import build_user_persona
from dailyai.storage.backend import get_user_daily_digest, store_user_daily_digest

logger = logging.getLogger("dailyai.services.personalizer_llm")

async def generate_daily_bespoke_digest(sync_code: str, articles: list[dict], force_refresh: bool = False) -> dict | None:
    """Generate or retrieve today's bespoke briefing via 1-LLM call."""
    if not articles:
        return None
        
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    
    # Return cache if available and not forced
    if not force_refresh:
        cached = await get_user_daily_digest(sync_code, date_str)
        if cached:
            logger.info(f"[Bespoke] Reusing cached digest for {sync_code}")
            return cached
            
    logger.info(f"[Bespoke] Generating 1-Call Digest for {sync_code}")
    persona = await build_user_persona(sync_code)
    
    # Prep top ~15 articles to minimize context window while providing good pool
    top_articles = []
    for a in articles[:15]:
        top_articles.append({
            "id": a.get("id"),
            "title": a.get("headline", a.get("title", "")),
            "summary": a.get("summary", ""),
            "topic": a.get("topic", a.get("category", "")),
        })
        
    articles_json = json.dumps(top_articles, indent=2)
    
    try:
        messages = BESPOKE_PROMPT.invoke({"persona": persona, "articles_json": articles_json})
        system_msg = messages.messages[0].content
        human_msg = messages.messages[1].content
        
        response = await invoke_llm(system_msg, human_msg, fast=False)
        
        # Clean response since it usually has ```json
        cleaned = response.replace('```json', '').replace('```', '').strip()
        data = json.loads(cleaned)
        
        # Ensure schema structure
        synthesis = data.get("daily_synthesis", "Your customized AI briefing is ready.")
        hooks = data.get("custom_hooks", {})
        
        await store_user_daily_digest(sync_code, date_str, synthesis, hooks)
        
        return {
            "synthesis": synthesis,
            "custom_hooks": hooks,
        }
    except Exception as e:
        logger.error(f"[Bespoke] Failed to generate personalization: {e}")
        return None
