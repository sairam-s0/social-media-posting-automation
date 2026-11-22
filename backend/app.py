"""AutoSocial Poster - Hardened Backend Server
Single-process, single-port architecture serving both the FastAPI REST API and
the static React single-page frontend.
"""
from __future__ import annotations

import hmac
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import (
    APP_NAME,
    HOST,
    PORT,
    DATABASE_PATH,
    FRONTEND_DIST,
    SESSION_TOKEN,
    LINKEDIN_REDIRECT_URI,
    REDDIT_REDIRECT_URI,
    DAILY_POST_CAP,
    MAX_SCHEDULE_DAYS,
    IS_PRODUCTION,
)
from database.db import init_db, get_db
from utils.vault import (
    save_secret,
    get_secret,
    mask_secret,
    delete_secret,
)
from utils.logging_config import logger
from utils.license_check import activate_license, get_license_status
from services.ai_service import generate_drafts
from services.oauth_service import (
    initiate_oauth_flow,
    handle_oauth_callback,
    get_platform_status,
    disconnect_platform,
    get_platform_credentials,
    get_platform_redirect_uri,
    reset_platform_credentials,
    is_platform_configured,
    is_shared_oauth,
)
from services.publisher_service import publish_post_idempotent
from services.scheduler import (
    scheduler_worker_loop,
    validate_schedule_time,
)

# Startup / Shutdown lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AutoSocial Poster backend...")
    init_db()

    # Pre-populate Groq key in vault from .env if present and not yet in vault
    env_groq = os.getenv("GROQ_API_KEY", "").strip()
    if env_groq and not get_secret("groq_api_key"):
        logger.info("Importing initial Groq API key from environment into encrypted vault.")
        save_secret("groq_api_key", env_groq)

    # Start background scheduler
    import asyncio
    worker_task = asyncio.create_task(scheduler_worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("AutoSocial Poster shutdown complete.")

app = FastAPI(
    title=APP_NAME,
    description="Automated LinkedIn and Reddit Publishing Engine",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
)

# Strict CORS: Only allow local loopback origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{PORT}",
        f"http://localhost:{PORT}",
        "http://127.0.0.1:5173",  # For development convenience
        "http://localhost:5173",
    ],
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Token", "Authorization"],
)

# Security Middleware: Session Token Authentication
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Allow CORS preflight and static assets freely
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path

    # Public/Unauthenticated paths
    public_paths = [
        "/api/health",
        "/api/bootstrap",
        "/health",
        "/auth/linkedin/callback",
        "/auth/reddit/callback",
        "/api/auth/linkedin/callback",
        "/api/auth/reddit/callback",
    ]

    is_public = path in public_paths or path.startswith("/auth/") or path.startswith("/api/auth/") or not path.startswith("/api/")

    if not is_public:
        auth_header = request.headers.get("X-Session-Token", "")
        # Cryptographic constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(auth_header.encode("utf-8"), SESSION_TOKEN.encode("utf-8")):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Unauthorized: Invalid or missing X-Session-Token."},
            )

    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"Unhandled exception during {request.method} {path}: {str(exc)}")
        # Production sanitized error response: Do not leak stack traces
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "An internal error occurred. Check local application logs."},
        )

# Request Models
class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    main_message: str = Field(min_length=1, max_length=2000)
    target_audience: str = Field(min_length=1, max_length=500)
    tone: str = "Thought Leadership"
    website_url: str = ""
    subreddit: str = "r/smallbusiness"
    reference_post: str = ""

class PostCreateRequest(BaseModel):
    topic: str
    platform: str
    content: str = Field(min_length=1, max_length=10000)
    destination: Optional[str] = None
    subreddit: Optional[str] = None
    status: str = "draft"  # "draft" | "scheduled"
    scheduled_at: Optional[str] = None
    timezone: Optional[str] = None

class PostUpdateRequest(BaseModel):
    content: Optional[str] = None
    destination: Optional[str] = None
    scheduled_at: Optional[str] = None
    timezone: Optional[str] = None
    topic: Optional[str] = None

class OAuthOpenBrowserRequest(BaseModel):
    redirect_uri: Optional[str] = None

class IntegrationSettingsRequest(BaseModel):
    groq_api_key: Optional[str] = None
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_redirect_uri: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: Optional[str] = None
    reddit_redirect_uri: Optional[str] = None

class LicenseActivateRequest(BaseModel):
    license_key: str

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
@app.get("/health")
def health():
    db_ok = DATABASE_PATH.exists()
    groq_ready = bool(get_secret("groq_api_key"))
    return {
        "status": "healthy",
        "app": APP_NAME,
        "database": "connected" if db_ok else "uninitialized",
        "groq_configured": groq_ready,
        "daily_cap": DAILY_POST_CAP,
    }

@app.get("/api/bootstrap")
def bootstrap():
    """Provides session token and config to local frontend on startup."""
    li_redirect = get_platform_redirect_uri("linkedin")
    rd_redirect = get_platform_redirect_uri("reddit")
    return {
        "session_token": SESSION_TOKEN,
        "port": PORT,
        "host": HOST,
        "api_base": "/api",
        "redirect_uris": {
            "linkedin": li_redirect,
            "reddit": rd_redirect,
            "registered_options": {
                "linkedin": [
                    f"http://127.0.0.1:{PORT}/auth/linkedin/callback",
                    f"http://localhost:{PORT}/auth/linkedin/callback",
                ],
                "reddit": [
                    f"http://127.0.0.1:{PORT}/auth/reddit/callback",
                    f"http://localhost:{PORT}/auth/reddit/callback",
                ]
            }
        },
        "shared_oauth": {
            "linkedin": is_shared_oauth("linkedin"),
            "reddit": is_shared_oauth("reddit"),
            "linkedin_configured": is_platform_configured("linkedin"),
            "reddit_configured": is_platform_configured("reddit"),
            "linkedin_has_custom": bool(get_secret("linkedin_client_id")),
            "reddit_has_custom": bool(get_secret("reddit_client_id")),
        },
        "limits": {
            "daily_cap": DAILY_POST_CAP,
            "max_schedule_days": MAX_SCHEDULE_DAYS,
        }
    }

@app.get("/api/accounts")
def accounts():
    """Return connection statuses for social platforms."""
    return {
        "linkedin": get_platform_status("linkedin"),
        "reddit": get_platform_status("reddit"),
    }

@app.post("/api/accounts/{platform}/disconnect")
def disconnect_account(platform: str):
    """Disconnect platform and wipe stored tokens."""
    if platform not in ("linkedin", "reddit"):
        raise HTTPException(400, "Unknown platform")
    disconnect_platform(platform)
    return {"success": True, "platform": platform, "status": "disconnected"}

@app.get("/api/settings/integrations")
def get_integrations_settings():
    """Return integration configuration status with MASKED secrets."""
    groq_raw = get_secret("groq_api_key")
    li_id, li_secret, _ = get_platform_credentials("linkedin")
    rd_id, rd_secret, rd_ua = get_platform_credentials("reddit")
    li_redirect = get_platform_redirect_uri("linkedin")
    rd_redirect = get_platform_redirect_uri("reddit")

    return {
        "groq": {
            "configured": bool(groq_raw),
            "masked": mask_secret(groq_raw),
        },
        "linkedin": {
            "configured": is_platform_configured("linkedin"),
            "shared_oauth": is_shared_oauth("linkedin"),
            "has_custom_credentials": bool(get_secret("linkedin_client_id")),
            "client_id_masked": mask_secret(li_id),
            "redirect_uri": li_redirect,
            "registered_redirect_uris": [
                f"http://127.0.0.1:{PORT}/auth/linkedin/callback",
                f"http://localhost:{PORT}/auth/linkedin/callback",
            ],
            "status": get_platform_status("linkedin"),
        },
        "reddit": {
            "configured": is_platform_configured("reddit"),
            "shared_oauth": is_shared_oauth("reddit"),
            "has_custom_credentials": bool(get_secret("reddit_client_id")),
            "client_id_masked": mask_secret(rd_id),
            "user_agent": rd_ua,
            "redirect_uri": rd_redirect,
            "registered_redirect_uris": [
                f"http://127.0.0.1:{PORT}/auth/reddit/callback",
                f"http://localhost:{PORT}/auth/reddit/callback",
            ],
            "status": get_platform_status("reddit"),
        },
    }

@app.post("/api/settings/integrations")
def save_integrations_settings(payload: IntegrationSettingsRequest):
    """Save integration credentials securely into OS credential vault."""
    saved_keys = []

    if payload.groq_api_key and payload.groq_api_key.strip():
        save_secret("groq_api_key", payload.groq_api_key.strip())
        saved_keys.append("groq_api_key")

    if payload.linkedin_client_id and payload.linkedin_client_id.strip():
        save_secret("linkedin_client_id", payload.linkedin_client_id.strip())
        saved_keys.append("linkedin_client_id")

    if payload.linkedin_client_secret and payload.linkedin_client_secret.strip():
        save_secret("linkedin_client_secret", payload.linkedin_client_secret.strip())
        saved_keys.append("linkedin_client_secret")

    if payload.linkedin_redirect_uri and payload.linkedin_redirect_uri.strip():
        save_secret("linkedin_redirect_uri", payload.linkedin_redirect_uri.strip())
        saved_keys.append("linkedin_redirect_uri")

    if payload.reddit_client_id and payload.reddit_client_id.strip():
        save_secret("reddit_client_id", payload.reddit_client_id.strip())
        saved_keys.append("reddit_client_id")

    if payload.reddit_client_secret and payload.reddit_client_secret.strip():
        save_secret("reddit_client_secret", payload.reddit_client_secret.strip())
        saved_keys.append("reddit_client_secret")

    if payload.reddit_user_agent and payload.reddit_user_agent.strip():
        save_secret("reddit_user_agent", payload.reddit_user_agent.strip())
        saved_keys.append("reddit_user_agent")

    if payload.reddit_redirect_uri and payload.reddit_redirect_uri.strip():
        save_secret("reddit_redirect_uri", payload.reddit_redirect_uri.strip())
        saved_keys.append("reddit_redirect_uri")

    logger.info(f"Updated credentials in encrypted vault: {', '.join(saved_keys)}")
    return {"success": True, "saved_keys": saved_keys}

@app.post("/api/settings/integrations/{platform}/reset-to-shared")
def reset_to_shared_credentials(platform: str):
    """Delete custom credentials and revert to central shared credentials."""
    if platform not in ("linkedin", "reddit"):
        raise HTTPException(400, "Unknown platform")
    reset_platform_credentials(platform)
    return {
        "success": True,
        "platform": platform,
        "shared_oauth": is_shared_oauth(platform),
        "configured": is_platform_configured(platform),
    }

@app.get("/api/license/status")
def license_status():
    return get_license_status()

@app.post("/api/license/activate")
def license_activate(payload: LicenseActivateRequest):
    result = activate_license(payload.license_key)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Activation failed."))
    return result

@app.post("/api/content/generate")
async def generate(req: GenerateRequest):
    return await generate_drafts(
        topic=req.topic,
        main_message=req.main_message,
        target_audience=req.target_audience,
        tone=req.tone,
        website_url=req.website_url,
        subreddit=req.subreddit,
        reference_post=req.reference_post,
    )

@app.get("/api/posts")
def list_posts():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/posts")
def create_post(req: PostCreateRequest):
    if req.platform not in ("linkedin", "reddit"):
        raise HTTPException(400, "Platform must be either 'linkedin' or 'reddit'.")

    post_id = secrets.token_urlsafe(12)
    destination = req.destination or req.subreddit or (
        "Personal Profile (Feed)" if req.platform == "linkedin" else "r/smallbusiness"
    )

    status_str = "scheduled" if req.status == "scheduled" else "draft"
    approved_int = 1 if status_str == "scheduled" else 0
    scheduled_at_iso = None

    if status_str == "scheduled":
        if not req.scheduled_at:
            raise HTTPException(400, "scheduled_at is mandatory when scheduling a post.")
        scheduled_at_iso = validate_schedule_time(req.scheduled_at)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO posts (id, topic, platform, destination, subreddit, content, status, approved, scheduled_at, timezone)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                post_id,
                req.topic.strip(),
                req.platform,
                destination.strip(),
                req.subreddit.strip() if req.subreddit else None,
                req.content.strip(),
                status_str,
                approved_int,
                scheduled_at_iso,
                req.timezone,
            ),
        )
        conn.commit()

    return {
        "id": post_id,
        "status": status_str,
        "approved": bool(approved_int),
        "destination": destination,
        "scheduled_at": scheduled_at_iso,
        "timezone": req.timezone,
    }

@app.patch("/api/posts/{post_id}")
def update_post(post_id: str, req: PostUpdateRequest):
    with get_db() as conn:
        post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post:
            raise HTTPException(404, "Post not found.")

        content = req.content.strip() if req.content is not None else post["content"]
        destination = req.destination.strip() if req.destination is not None else post["destination"]
        topic = req.topic.strip() if req.topic is not None else post["topic"]
        tz = req.timezone if req.timezone is not None else post["timezone"]

        scheduled_at_iso = post["scheduled_at"]
        if req.scheduled_at:
            scheduled_at_iso = validate_schedule_time(req.scheduled_at)

        conn.execute(
            """UPDATE posts SET content = ?, destination = ?, scheduled_at = ?, timezone = ?, topic = ?
               WHERE id = ?""",
            (content, destination, scheduled_at_iso, tz, topic, post_id),
        )
        conn.commit()

    return {
        "id": post_id,
        "status": post["status"],
        "approved": bool(post["approved"]),
        "content": content,
        "destination": destination,
        "scheduled_at": scheduled_at_iso,
        "timezone": tz,
        "topic": topic,
    }

@app.post("/api/posts/{post_id}/publish")
async def publish_now(post_id: str):
    return await publish_post_idempotent(post_id)

@app.post("/api/posts/{post_id}/cancel")
def cancel_post(post_id: str):
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE posts SET status = 'cancelled' WHERE id = ? AND status IN ('scheduled', 'draft', 'missed')",
            (post_id,),
        )
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Post not found or cannot be cancelled.")
    return {"id": post_id, "status": "cancelled"}

@app.delete("/api/posts/{post_id}")
def delete_post(post_id: str):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Post not found.")
    return {"id": post_id, "status": "deleted"}

# ---------------------------------------------------------------------------
# OAuth Authorization Endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/{platform}/open-browser")
@app.post("/api/auth/{platform}/open-browser")
def oauth_open_browser(platform: str, req: Optional[OAuthOpenBrowserRequest] = None):
    """Open platform authorization URL directly in the OS default browser for native app flow."""
    import webbrowser
    custom_uri = req.redirect_uri if req and req.redirect_uri else None
    redirect_target = initiate_oauth_flow(platform, custom_redirect_uri=custom_uri)
    logger.info(f"Opening {platform} authorization URL in OS default browser: {redirect_target}")
    opened = webbrowser.open(redirect_target)
    return {"success": True, "opened": opened, "url": redirect_target}

@app.get("/auth/{platform}")
@app.get("/api/auth/{platform}")
def oauth_start(platform: str, system_browser: bool = False, redirect_uri: Optional[str] = None):
    redirect_target = initiate_oauth_flow(platform, custom_redirect_uri=redirect_uri)
    if system_browser:
        import webbrowser
        webbrowser.open(redirect_target)
        return HTMLResponse(
            f"""<!DOCTYPE html><html><body style="font-family:sans-serif;padding:30px;background:#FAF8F5;color:#2C352B;text-align:center;">
            <h3>Opening {platform.title()} in your default browser...</h3>
            <p>Please complete authorization in the browser window that just opened.</p>
            <p>You can close this window and return to AutoSocial Poster.</p>
            <script>setTimeout(function() {{ window.close(); }}, 3000);</script>
            </body></html>"""
        )
    return RedirectResponse(redirect_target)

@app.get("/auth/{platform}/callback")
@app.get("/api/auth/{platform}/callback")
async def oauth_callback(platform: str, request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return HTMLResponse(
            f"""<!DOCTYPE html><html><body style="font-family:sans-serif;padding:30px;background:#fdf2f2;color:#8c2a2a;">
            <h2>Authorization Cancelled or Failed</h2>
            <p>Provider returned error: <code>{error}</code></p>
            <p>You can close this tab and return to AutoSocial Poster.</p>
            </body></html>""",
            status_code=400,
        )

    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state parameter.")

    stored = await handle_oauth_callback(platform, code, state)
    account_name = stored.get("account_name") or "Connected Account"

    return HTMLResponse(
        f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{platform.title()} Connected</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #FAF8F5; color: #2C352B; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
    .card {{ background: white; border: 1px solid #E5E0D8; border-radius: 16px; padding: 32px; max-width: 440px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .badge {{ display: inline-block; background: #E2EBDD; color: #2E542B; padding: 6px 14px; border-radius: 999px; font-weight: 600; font-size: 13px; margin-bottom: 16px; }}
    h2 {{ margin: 0 0 10px; font-size: 20px; }}
    p {{ color: #6B7569; font-size: 14px; margin: 0 0 20px; }}
    button {{ background: #3F513D; color: white; border: none; border-radius: 8px; padding: 10px 20px; font-weight: 600; cursor: pointer; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">Connection Successful</div>
    <h2>{platform.title()} Account Linked!</h2>
    <p>Authorized Account: <strong>{account_name}</strong></p>
    <p>Tokens stored securely in Windows Credential Manager. You can now return to the AutoSocial Poster app window.</p>
    <button onclick="window.close()">Close Window</button>
  </div>
  <script>
    if (window.opener) {{
      try {{ window.opener.postMessage({{ type: 'OAUTH_SUCCESS', platform: '{platform}' }}, '*'); }} catch (e) {{}}
    }}
  </script>
</body>
</html>"""
    )

# ---------------------------------------------------------------------------
# Static Files & SPA Routing
# ---------------------------------------------------------------------------

# Mount static asset folders if they exist
assets_dir = FRONTEND_DIST / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve built React single-page application with guaranteed session token injection."""
    # Never intercept API or Auth routes
    if full_path.startswith("api/") or full_path.startswith("auth/"):
        raise HTTPException(404, "Endpoint not found.")

    clean_path = full_path.strip("/")

    # If requesting a concrete static file asset (excluding index.html), serve directly if exists
    if clean_path and clean_path != "index.html":
        target_file = FRONTEND_DIST / clean_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)

    # For root (/), index.html, and all SPA navigation routes, serve index.html with window.__APP_CONFIG__ injected
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
        # Seamlessly inject per-launch session token and fixed port configuration
        injection = f"""<script>
window.__APP_CONFIG__ = {{
  sessionToken: "{SESSION_TOKEN}",
  host: "{HOST}",
  port: {PORT},
  apiBase: "/api"
}};
</script>"""
        if "</head>" in content:
            modified = content.replace("</head>", f"{injection}\n</head>")
        elif "<head>" in content:
            modified = content.replace("<head>", f"<head>\n{injection}")
        else:
            modified = injection + content
        return HTMLResponse(modified)

    return HTMLResponse(
        """<!DOCTYPE html><html><body style="font-family:sans-serif;padding:40px;text-align:center;">
        <h2>AutoSocial Poster Backend Running</h2>
        <p>Vite frontend static build not found yet at <code>dist/index.html</code>.</p>
        <p>Run <code>npm run build</code> to produce production bundle.</p>
        </body></html>"""
    )

if __name__ == "__main__":
    logger.info(f"Starting AutoSocial Poster server on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
