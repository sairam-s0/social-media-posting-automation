import os
import sys

OUTPUT_FILE = r"e:\temp\edulenza\ai_automation\social-media-posting-automation\codebase_freelancing.md"
ROOT_DIR = r"e:\temp\edulenza\ai_automation\social-media-posting-automation"

FILES_TO_INCLUDE = [
    (".env.example", "properties", "Environment Variables Template"),
    (".gitignore", "gitignore", "Git Ignore Rules"),
    ("package.json", "json", "Node.js Package Configuration & Dependencies"),
    ("requirements.txt", "text", "Python Backend Dependencies"),
    ("vite.config.js", "javascript", "Vite Build Configuration & Proxy"),
    ("AutoSocialPoster.spec", "python", "PyInstaller Build Specification"),
    ("build_production.py", "python", "Production Build & Verification Automation Script"),
    ("installer.iss", "ini", "Inno Setup Windows Installer Script"),
    ("sign_build.bat", "bat", "Code Signing Utility Script"),
    ("index.html", "html", "Frontend HTML Entry Point with Config Injection Anchor"),
    ("src/main.jsx", "jsx", "React Main Entry Point & Session Token Bootstrap Hook"),
    ("src/App.jsx", "jsx", "React Application Root Wrapper"),
    ("src/CalendarPicker.jsx", "jsx", "7-Day Window Calendar Picker Component"),
    ("src/style.css", "css", "Global Styles & Tailwind CSS Directives"),
    ("linkedin_reddit_social_media_automation_mvp.tsx", "tsx", "Master Frontend Application (UI, State, API Client, OAuth Manager)"),
    ("backend/__init__.py", "python", "Backend Package Init"),
    ("backend/app.py", "python", "FastAPI Application Server, Routes, and Security Middleware"),
    ("backend/config.py", "python", "Configuration Management, Paths & AppData Resolution"),
    ("backend/launcher.py", "python", "Desktop Application Launcher, PyWebView & Single-Instance Mutex"),
    ("backend/database/__init__.py", "python", "Database Package Init"),
    ("backend/database/db.py", "python", "SQLite Schema Definition, Migration & Data Access"),
    ("backend/services/__init__.py", "python", "Services Package Init"),
    ("backend/services/ai_service.py", "python", "AI Content Generation Service (Groq API + Offline Fallback)"),
    ("backend/services/oauth_service.py", "python", "OAuth 2.0 PKCE Engine (LinkedIn & Reddit Authentication)"),
    ("backend/services/publisher_service.py", "python", "Social Publishing Engine (LinkedIn UGC & Reddit API)"),
    ("backend/services/scheduler.py", "python", "Background Scheduler & Daily Post Rate Limiter"),
    ("backend/utils/__init__.py", "python", "Utilities Package Init"),
    ("backend/utils/license_check.py", "python", "Hardware & Installation License Verification Utility"),
    ("backend/utils/logging_config.py", "python", "Centralized Structured Logging Configuration"),
    ("backend/utils/single_instance.py", "python", "Windows Named Mutex Single-Instance Lock"),
    ("backend/utils/vault.py", "python", "Windows Credential Manager DPAPI Vault Utility"),
    ("backend/tests/test_multi_user_isolation.py", "python", "Multi-User Windows Profile Isolation Test"),
    ("backend/tests/test_production_verification.py", "python", "Comprehensive 13-Point Production Verification Test Suite"),
    ("generate_codebase_md.py", "python", "Automated Master Documentation & Codebase Markdown Generator"),
]

DOC_HEADER = """# AutoSocial Poster - Complete Codebase & System Architecture

> **Comprehensive Project Documentation & Master Source Code Archive**  
> **Product Version:** 1.0.0 (Production Hardened)  
> **Target Platform:** Windows 10 / Windows 11 (x64)  
> **Primary Technology Stack:** React 19 + Vite + Tailwind CSS v4 + FastAPI + SQLite + PyWebView + PyInstaller + Inno Setup

---

## 1. Executive System Overview

**AutoSocial Poster** is a professional-grade, standalone Windows desktop application for automated social media scheduling, AI-assisted content drafting, and multi-platform publishing across **LinkedIn** and **Reddit**.

The software is engineered with a strict local-first, zero-leakage security model:
1. **Zero Cloud Telemetry or Credential Leakage:** All sensitive API keys, user OAuth tokens, and client secrets are stored exclusively on the user's machine using Windows Data Protection API (DPAPI via `keyring`).
2. **Central Shared vs. Custom Developer App Dual-Mode OAuth:** Out of the box, end users do not need to register developer accounts or configure client secrets; the backend transparently orchestrates authentication through central developer credentials. Advanced users can seamlessly configure custom developer apps with dynamic loopback redirect URI management and 1-click fallback.
3. **Session-Locked Localhost Architecture:** The frontend Single-Page Application (SPA) communicates with the backend FastAPI service over a cryptographically authenticated loopback bridge (`X-Session-Token` with constant-time HMAC comparison).
4. **Desktop Native Delivery:** Bundled as a single self-contained Windows executable and standard Inno Setup installer with automatic dependency bundling (Python 3.11 runtime, OpenSSL, SQLite, and Visual C++ runtimes).

---

## 2. High-Level Architecture & Component Stack

```
+-----------------------------------------------------------------------------------+
|                            WINDOWS DESKTOP RUNTIME                                |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 PyWebView Native Shell (WebView2 / WinForms)                |  |
|  |                                                                             |  |
|  |   +---------------------------------------------------------------------+   |  |
|  |   |             React 19 Single Page Application (SPA)                  |   |  |
|  |   |                                                                     |   |  |
|  |   |   * Post Creation & Multi-Platform Matrix (LinkedIn / Reddit)       |   |  |
|  |   |   * 7-Day Window Calendar Picker (Strict 7-Day Forward Limit)       |   |  |
|  |   |   * Groq AI Content Drafter (Streaming & Template Fallback)         |   |  |
|  |   |   * Connected Accounts & OAuth Central/Custom App Manager           |   |  |
|  |   |   * Post History, Status Badges, Logs & Analytics Overview          |   |  |
|  |   +---------------------------------------------------------------------+   |  |
|  +--------------------------------------|--------------------------------------+  |
|                                         | Loopback HTTP (127.0.0.1:8000)          |
|                                         | Headers: X-Session-Token (HMAC)         |
|  +--------------------------------------v--------------------------------------+  |
|  |                      FastAPI ASGI Backend (Uvicorn)                         |  |
|  |                                                                             |  |
|  |   * Security Middleware (Constant-time token validation)                    |  |
|  |   * OAuth 2.0 PKCE Engine (Dynamic redirect URI: 127.0.0.1 & localhost)     |  |
|  |   * Publisher Engine (LinkedIn UGC API & Reddit OAuth API)                  |  |
|  |   * Background Scheduler Thread (60s tick, daily cap enforcement)           |  |
|  |   * Groq AI Integration (openai/gpt-oss-120b)                               |  |
|  |   * Single-Instance Lock (Global\\AutoSocialPoster_SingleInstance_Mutex)    |  |
|  +-----------------------------------------------------------------------------+  |
|           |                                                      |                |
|           v                                                      v                |
|  +------------------------------------+      +---------------------------------+  |
|  |   SQLite Database                  |      | Windows Credential Manager      |  |
|  |   %APPDATA%\\AutoSocialPoster\\     |      | DPAPI Secure Vault              |  |
|  |   data\\social_automation.sqlite3   |      | Tokens, Client Secrets, Keys    |  |
|  +------------------------------------+      +---------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Component Breakdown

| Layer | Technologies | Responsibilities |
| :--- | :--- | :--- |
| **Frontend UI** | React 19, Vite 6, Tailwind CSS v4, Lucide React | Presentation, drafting, scheduling, 7-day calendar, account linking, settings. |
| **Desktop Shell** | PyWebView, Microsoft Edge WebView2, WinForms | Native desktop window frame, system tray, single instance enforcement. |
| **Backend API** | Python 3.11, FastAPI, Starlette, Uvicorn | Session auth middleware, REST endpoints, HTML config injection, static SPA hosting. |
| **OAuth 2.0 PKCE** | `httpx`, `secrets`, `hashlib` | Dynamic redirect URI negotiation, PKCE challenge generation, token exchange & refresh. |
| **Social Publishing** | LinkedIn UGC API (`restli`), Reddit API | Image/text post dispatch, rate limit backoff, post status updates. |
| **Scheduling Engine** | Python daemon thread, SQLite queries | Forward date validation (<= 7 days), daily post capping (default 5/day), queue worker. |
| **Storage & Security** | SQLite3, `keyring` (Windows DPAPI) | Account isolation per Windows profile, encrypted OAuth tokens, secret masking. |
| **Packaging & CI** | PyInstaller, Inno Setup, PowerShell | Standalone EXE packaging, DLL dependency bundling, Windows installer generation. |

---

## 3. Core Security & Authentication Model

### 3.1 Ephemeral Session Token Protection
* **Generation:** On startup, `backend/launcher.py` generates a cryptographically secure 32-byte session token (`secrets.token_urlsafe(32)`).
* **Dual-Channel Frontend Handshake:**
  1. **Packaged Desktop App:** When FastAPI serves `GET /` or `GET /index.html`, it dynamically injects `<script>window.__APP_CONFIG__ = { sessionToken: "...", port: 8000, ... };</script>` directly into the HTML `<head>`.
  2. **Vite Development Server (`localhost:5173`):** During local development, the frontend calls `GET /api/bootstrap` before mounting the React DOM (`initSessionConfig()` in `src/main.jsx`), discovering the active session token and server configuration.
* **Middleware Enforcement:** Every protected API route (`/api/*`) requires the `X-Session-Token` header. The middleware performs a constant-time HMAC comparison using `hmac.compare_digest()` to eliminate timing attacks.
* **Public Exemption Allowlist:** Only `/api/health`, `/api/bootstrap`, and `/api/auth/{platform}/callback` are publicly accessible without a session token.
* **Automatic 401 Recovery:** The frontend API client (`apiRequest()`) intercepts unexpected 401 errors, triggers a one-time automatic bootstrap refresh, and retries the request seamlessly.

### 3.2 Windows Credential Manager DPAPI Vault
* No plaintext passwords, OAuth client secrets, or user access/refresh tokens are ever written to the SQLite database or disk files.
* All secrets are stored in the Windows Credential Vault under service namespace `AutoSocialPoster` using Windows Data Protection API (DPAPI).
* **Secret Masking:** When frontend requests `/api/settings/integrations`, all client secrets and API keys are returned as masked indicators (`••••••••`) if present, or `null` if unconfigured. Cleartext secrets are never exposed in GET responses.
* **Safe Updates:** Submitting empty string (`""`) for a secret field in Settings preserves the existing stored secret rather than erasing it.
* **Safeguard against Dummy Placeholders:** The backend filters out placeholder strings (e.g., `shared_...`) so that unconfigured central credentials are never sent to external OAuth endpoints.

### 3.3 Multi-User Profile Isolation
* Application data is strictly isolated per Windows user account using the standard Windows `%APPDATA%` environment variable:
  ```
  C:\\Users\\<Username>\\AppData\\Roaming\\AutoSocialPoster\\data\\social_automation.sqlite3
  C:\\Users\\<Username>\\AppData\\Roaming\\AutoSocialPoster\\logs\\autosocial.log
  ```
* Different Windows user accounts running on the same PC cannot access or overwrite each other's database or vault credentials.

---

## 4. OAuth 2.0 Integration & Setup Guide

### 4.1 Central Shared App vs. Custom Developer App
The application implements a hybrid credential architecture:
1. **Central Shared App (Default):**
   - Developer credentials (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `REDDIT_CLIENT_ID`, etc.) are configured centrally on the backend.
   - End users do not need to register a developer app, generate secrets, or understand OAuth redirect URIs.
2. **Custom Developer App Override (Power User):**
   - Users can enter their own Client ID and Client Secret in **Settings -> Integrations**.
   - Custom credentials immediately override shared credentials.
   - A warning banner is displayed in the UI whenever custom credentials are active.
3. **1-Click Reset to Shared:**
   - The UI includes a prominent **"↺ Revert to Central Shared App"** button (`POST /api/settings/integrations/{platform}/reset-to-shared`) to instantly remove custom overrides and restore shared defaults.

### 4.2 Handling Redirect URI Mismatches (`127.0.0.1` vs `localhost`)
Major identity providers (LinkedIn and Reddit) require an exact byte-for-byte string match with the registered Redirect URI in the developer console. If `http://localhost:8000/...` is registered but the application sends `http://127.0.0.1:8000/...`, the authorization fails with:
```
Bummer, something went wrong.
The redirect_uri does not match the registered value
```
**AutoSocial Poster Engineering Resolution:**
* The backend dynamically tracks the exact `redirect_uri` requested during `initiate_oauth_flow()` and stores it alongside the CSRF `state` in `OAUTH_STATES`.
* During callback exchange (`handle_oauth_callback()`), the exact same URI is supplied for token exchange.
* The frontend Settings page displays 1-click **Copy** buttons for both standard loopback variants:
  * `http://127.0.0.1:8000/auth/linkedin/callback`
  * `http://localhost:8000/auth/linkedin/callback`
* The UI includes a direct loopback switcher (`Set 127.0.0.1` / `Set localhost`) so users can match their developer console with one click.

### 4.3 LinkedIn Developer Portal Checklist
1. Navigate to [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Create an App and associate a LinkedIn Page.
3. Under the **Products** tab, add:
   * **Share on LinkedIn**
   * **Sign In with LinkedIn using OpenID Connect**
4. Under the **Auth** tab, under **Authorized redirect URLs for your app**, add BOTH:
   * `http://127.0.0.1:8000/auth/linkedin/callback`
   * `http://localhost:8000/auth/linkedin/callback`
5. Note the **Client ID** and **Primary Client Secret**.

### 4.4 Reddit Developer Portal Checklist
1. Navigate to [Reddit App Preferences](https://www.reddit.com/prefs/apps).
2. Click **create another app...** (or create app).
3. Select **installed app** (or **web app**).
4. Set **redirect uri** to BOTH:
   * `http://127.0.0.1:8000/auth/reddit/callback`
   * `http://localhost:8000/auth/reddit/callback`
5. Note the Client ID (under the app name) and Secret.

---

## 5. Post Scheduling & Rate Limiting Engine

### 5.1 Strict 7-Day Allowed Forward Scheduling Window
To ensure content relevance and comply with platform API scheduling boundaries:
* Posts can only be scheduled between **Today** and **Today + 7 Days**.
* **Frontend Enforcement:** The embedded `CalendarPicker.jsx` visualizes the allowed window, locks days beyond the 7-day limit with visual lock icons (`Lock` icon), disables click actions, and highlights the active window range.
* **Backend Validator:** `validate_schedule_time()` rejects any timestamp earlier than current time or later than `now + 7 days` with a descriptive `400 Bad Request` HTTP error.

### 5.2 Daily Rate Limit Cap
* Default limit: **5 posts per day** (configurable via `DAILY_POST_CAP` in `.env` and Settings).
* Evaluated against successful and scheduled posts for the target calendar date in SQLite.
* Protects user accounts from spam detection flags and API quota exhaustion.

---

## 6. Complete API Route Specification

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/health` | No | System health check, uptime, version, and database status. |
| `GET` | `/api/bootstrap` | No | Session token, host, port, redirect URIs, and config discovery. |
| `GET` | `/` & `/index.html` | No | Serves SPA HTML with injected `window.__APP_CONFIG__` script. |
| `GET` | `/auth/{platform}/login` | Yes | Initiates OAuth flow, generates PKCE, redirects browser. |
| `GET` | `/auth/{platform}/callback`| No | Public OAuth callback endpoint; exchanges code for access token. |
| `GET` | `/api/accounts` | Yes | Lists all connected social media accounts and active status. |
| `DELETE`| `/api/accounts/{platform}`| Yes | Disconnects account, clears DPAPI tokens and SQLite records. |
| `GET` | `/api/posts` | Yes | Fetches all scheduled, published, and draft posts with metadata. |
| `POST` | `/api/posts` | Yes | Creates and schedules a post with 7-day and daily cap checks. |
| `POST` | `/api/posts/{id}/publish-now` | Yes | Immediately publishes a scheduled or draft post. |
| `DELETE`| `/api/posts/{id}` | Yes | Cancels and deletes a scheduled post. |
| `POST` | `/api/generate-content` | Yes | Generates post content via Groq AI (with offline fallback). |
| `GET` | `/api/settings/integrations` | Yes | Retrieves integration config with masked secrets. |
| `POST` | `/api/settings/integrations` | Yes | Saves custom developer app credentials to DPAPI vault. |
| `POST` | `/api/settings/integrations/{platform}/reset-to-shared` | Yes | Resets custom credentials back to shared defaults. |
| `GET` | `/api/stats` | Yes | Summary analytics: scheduled count, published count, platform breakdown. |
| `GET` | `/api/logs` | Yes | Recent application execution logs. |

---

## 7. Build, Packaging & Verification Guide

### 7.1 Development Mode
```bash
# Terminal 1: Frontend Dev Server (Vite)
npm run dev

# Terminal 2: Backend Dev Server (Uvicorn)
.venv\\Scripts\\uvicorn app:app --reload --app-dir backend --port 8000
```

### 7.2 Automated Test Execution
```bash
# Run comprehensive 13-point production verification test
.venv\\Scripts\\python.exe backend/tests/test_production_verification.py

# Run Windows user profile data isolation test
.venv\\Scripts\\python.exe backend/tests/test_multi_user_isolation.py
```

### 7.3 Production Executable Build
```bash
# Automated 1-step build script:
# 1. Compiles React production bundle (npm run build -> dist/)
# 2. Bundles Python runtime and Windows DLLs via PyInstaller
# 3. Performs self-check headless verification (auto posted v2.exe --check)
python build_production.py
```

### 7.4 Inno Setup Installer Generation
Compile `installer.iss` using Inno Setup 6:
```bash
"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" installer.iss
```
Generates `installer_dist/AutoSocialPoster_Setup_v1.0.0.exe`.

---

## 8. Master Project File Tree

```
social-media-posting-automation/
├── .env.example
├── .gitignore
├── package.json
├── requirements.txt
├── vite.config.js
├── AutoSocialPoster.spec
├── build_production.py
├── installer.iss
├── sign_build.bat
├── index.html
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── CalendarPicker.jsx
│   └── style.css
├── linkedin_reddit_social_media_automation_mvp.tsx
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── launcher.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── oauth_service.py
│   │   ├── publisher_service.py
│   └── scheduler.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── license_check.py
│   │   ├── logging_config.py
│   │   ├── single_instance.py
│   │   └── vault.py
│   └── tests/
│       ├── test_multi_user_isolation.py
│       └── test_production_verification.py
```

---

## 9. Complete Project Source Code

The following sections contain the complete, verbatim source code for every file in the project.

"""

def main():
    print("Beginning generation of codebase_freelancing.md...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(DOC_HEADER)
        
        for rel_path, lang, desc in FILES_TO_INCLUDE:
            abs_path = os.path.join(ROOT_DIR, rel_path.replace("/", os.sep))
            if not os.path.exists(abs_path):
                print(f"ERROR: Missing file {abs_path}")
                sys.exit(1)
            
            print(f"Adding: {rel_path} ({desc})")
            out.write(f"### {rel_path}\n\n")
            out.write(f"> **Purpose:** {desc}  \n")
            out.write(f"> **File Path:** `{rel_path}`\n\n")
            out.write(f"```{lang}\n")
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as src:
                content = src.read()
                out.write(content)
                if not content.endswith("\n"):
                    out.write("\n")
            out.write("```\n\n---\n\n")

    size = os.path.getsize(OUTPUT_FILE)
    print(f"SUCCESS: Generated {OUTPUT_FILE} (size: {size} bytes, {size/1024:.1f} KB)")

if __name__ == "__main__":
    main()
