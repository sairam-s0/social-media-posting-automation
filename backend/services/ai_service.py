"""AI content draft generation service using Groq API.
Enforces strict input length constraints and output sanitization.
"""
from __future__ import annotations

import json
import os
import re
import httpx
from fastapi import HTTPException
from config import (
    MAX_INPUT_TOPIC_LENGTH,
    MAX_INPUT_MESSAGE_LENGTH,
    MAX_INPUT_AUDIENCE_LENGTH,
    MAX_INPUT_REFERENCE_LENGTH,
)
from utils.vault import get_secret
from utils.logging_config import logger

SYSTEM_PROMPT = """You are an elite B2B social media strategist and executive ghostwriter.
You specialize in writing high-performing, viral LinkedIn posts and authentic, high-upvote Reddit community discussions.

Your task is to take the provided core inputs and craft TWO distinct, platform-native drafts in a single API response.
When a Reference Post / Inspiration is provided, carefully analyze its style, rhythm, structure, angle, or lesson, and adapt the new topic and value proposition accordingly while keeping the content fresh, original, and platform-appropriate. If no reference post is provided, craft standard best-in-class posts based on the topic and guidelines.

### 1. LINKEDIN POST RULES:
- **Hook**: Start with a punchy 1-2 sentence hook that stops the scroll (highlight a sharp insight, counter-intuitive truth, or quantifiable metric).
- **Structure & Spacing**:
  - Write in skimmable, short paragraphs (1-2 sentences max per block).
  - Use generous whitespace.
  - Use bullet points (•, ➔, or 1., 2., 3.) for key insights, frameworks, or takeaways.
  - Never generate monolithic blocks of text.
- **Value & Authority**: Position the post with authority, speaking directly to the specified Target Audience in the requested Tone.
- **Engagement Question**: Conclude with a thought-provoking question that prompts comments and peer discussions.
- **Optional CTA Link**:
  - ONLY if a valid Website URL is explicitly provided, integrate a clean callout before hashtags (e.g. "🔗 See the live workflow: [URL]" or "Check out how it works: [URL]").
  - If NO Website URL is provided, DO NOT include any link, URL, or placeholder. Do not mention visiting a website or link in bio.
- **MANDATORY Hashtags**:
  - You MUST include 3 to 5 highly relevant hashtags on a new line at the very end of the LinkedIn post.
  - Tailor the hashtags specifically to the Target Audience, niche, and topic (e.g., #SmallBusiness #Operations #AIAutomation #FounderTips #Productivity).

### 2. REDDIT POST RULES:
- **Header Format**:
  - The FIRST line MUST start with: "Title: [Authentic, intriguing Reddit title without corporate buzzwords]"
  - Followed by a blank line, then the body in clean Markdown format.
- **Tone & Culture**:
  - Write like a real practitioner/founder sharing an unfiltered breakdown or lesson with peers.
  - Strictly avoid marketing jargon, corporate buzzwords, and promotional hype (Reddit severely downvotes sales pitches).
  - Provide direct, honest value (what was tested, exact numbers, what worked, what failed).
- **Subreddit Alignment**: Fit naturally into the culture of the target subreddit.
- **Community Discussion**:
  - End with an open-ended question inviting the subreddit community to share their experience, tools, or critique.
- **Optional CTA Link**:
  - ONLY if a valid Website URL is explicitly provided, you may mention it humbly at the end as an optional reference (e.g. "If helpful, I put together a demo here: [URL]").
  - If NO Website URL is provided, DO NOT mention any link, demo, or website at all.
- **NO Hashtags**: Never use hashtags on Reddit.

### OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object matching this exact schema:
{
  "linkedin": "<complete LinkedIn post including hook, body, discussion question, optional CTA link, and 3-5 audience hashtags>",
  "reddit": "<complete Reddit post starting with 'Title: ...' followed by blank line and body, no hashtags>"
}"""

def sanitize_text(text: str) -> str:
    """Strip malicious script tags, HTML tags, or dangerous control characters."""
    if not text:
        return ""
    # Strip dangerous HTML/script tags
    clean = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", "", clean, flags=re.IGNORECASE | re.DOTALL)
    # Strip null bytes and non-printable control characters except newline and tab
    clean = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", clean)
    return clean.strip()

async def generate_drafts(
    topic: str,
    main_message: str,
    target_audience: str,
    tone: str = "Thought Leadership",
    website_url: str = "",
    subreddit: str = "r/smallbusiness",
    reference_post: str = ""
) -> dict[str, str]:
    """Generate platform-specific drafts using Groq API."""
    # Retrieve key from vault first, fallback to env for initial setup
    api_key = get_secret("groq_api_key") or os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            503,
            "Groq API Key is not configured. Please enter your Groq API Key in Settings > Integrations."
        )

    # Input length capping
    clean_topic = sanitize_text(topic)[:MAX_INPUT_TOPIC_LENGTH]
    clean_msg = sanitize_text(main_message)[:MAX_INPUT_MESSAGE_LENGTH]
    clean_audience = sanitize_text(target_audience)[:MAX_INPUT_AUDIENCE_LENGTH]
    clean_tone = sanitize_text(tone)[:100] or "Thought Leadership"
    clean_sub = sanitize_text(subreddit)[:100] or "r/smallbusiness"
    clean_url = sanitize_text(website_url)[:255]
    clean_ref = sanitize_text(reference_post)[:MAX_INPUT_REFERENCE_LENGTH]

    url_instruction = clean_url if clean_url else "None (No URL provided. Do NOT mention any website, link, or CTA link in either post.)"

    ref_instruction = f"\nReference Post / Style Example:\n\"\"\"\n{clean_ref}\n\"\"\"\n(Analyze the structure, tone, or narrative progression of this reference and adapt your drafts accordingly.)" if clean_ref else "None (No reference post provided.)"

    user_prompt = f"""Topic: {clean_topic}
Main Message / Value Proposition: {clean_msg}
Target Audience: {clean_audience}
Tone: {clean_tone}
Target Subreddit: {clean_sub}
Website URL: {url_instruction}
Reference Post: {ref_instruction}"""

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    logger.info(f"Generating drafts via Groq model: {model} for topic: {clean_topic[:50]}...")

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
        except httpx.RequestError as exc:
            logger.error(f"Network error connecting to Groq API: {exc}")
            raise HTTPException(502, f"Failed to connect to Groq API: {str(exc)}")

    if response.is_error:
        logger.error(f"Groq API returned error status {response.status_code}")
        raise HTTPException(response.status_code, "Groq generation failed. Verify API key and spend quota.")

    try:
        raw_json = response.json()["choices"][0]["message"]["content"]
        content = json.loads(raw_json)
        linkedin_text = sanitize_text(content.get("linkedin", ""))
        reddit_text = sanitize_text(content.get("reddit", ""))

        if not linkedin_text or not reddit_text:
            raise ValueError("Draft payload missing linkedin or reddit keys")

        return {
            "linkedin": linkedin_text,
            "reddit": reddit_text
        }
    except Exception as e:
        logger.error(f"Invalid draft response from Groq: {e}")
        raise HTTPException(502, "Groq returned an unexpected draft structure.")
