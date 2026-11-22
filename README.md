# AutoSocial Poster

> **Professional, local-first Windows desktop suite for AI-powered social media scheduling and automated publishing across LinkedIn and Reddit.**

[![Target Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(x64)-blue.svg)](#)
[![Stack](https://img.shields.io/badge/Stack-React%2019%20%2B%20FastAPI%20%2B%20SQLite-green.svg)](#)
[![Packaging](https://img.shields.io/badge/Packaging-PyInstaller%20%2B%20Inno%20Setup-orange.svg)](#)
[![Security](https://img.shields.io/badge/Security-Windows%20DPAPI%20Vault%20%2B%20HMAC-red.svg)](#)

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Key Architecture & Security Model](#key-architecture--security-model)
3. [Core Feature Breakdown](#core-feature-breakdown)
   - [AI Content Generation (Groq)](#1-ai-content-generation-groq)
   - [Post Scheduling & Strict 7-Day Calendar](#2-post-scheduling--strict-7-day-calendar)
   - [Multi-Platform Publishing Engine](#3-multi-platform-publishing-engine)
   - [Dual-Mode OAuth 2.0 Integration](#4-dual-mode-oauth-20-integration)
   - [Real-Time Terminal & Execution Logs](#5-real-time-terminal--execution-logs)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Prerequisites & Development Setup](#prerequisites--development-setup)
7. [Running in Development Mode](#running-in-development-mode)
8. [Automated Testing & Verification](#automated-testing--verification)
9. [Production Packaging & Installer Compilation](#production-packaging--installer-compilation)
10. [Configuration & Environment Variables](#configuration--environment-variables)
11. [OAuth Developer Portal Checklist](#oauth-developer-portal-checklist)
12. [Product Activation & Licensing](#product-activation--licensing)

---

## Executive Overview

**AutoSocial Poster** is an enterprise-grade, standalone Windows desktop application designed for founders, marketers, and content creators to draft, schedule, and automate social media publications.

All sensitive operations run **locally on your machine**. There is zero telemetry, no external database, and credentials are never stored in plaintext or transferred to third-party cloud servers.

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
|  |   * Single-Instance Lock (Global\AutoSocialPoster_SingleInstance_Mutex)    |  |
|  +-----------------------------------------------------------------------------+  |
|           |                                                      |                |
|           v                                                      v                |
|  +------------------------------------+      +---------------------------------+  |
|  |   SQLite Database                  |      | Windows Credential Manager      |  |
|  |   %APPDATA%\AutoSocialPoster\      |      | DPAPI Secure Vault              |  |
|  |   data\social_automation.sqlite3   |      | Tokens, Client Secrets, Keys    |  |
|  +------------------------------------+      +---------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## Key Architecture & Security Model

### 1. Windows DPAPI Secure Vault (`keyring`)
* OAuth access tokens, refresh tokens, client secrets, and Groq API keys are stored encrypted via the **Windows Credential Manager / Data Protection API (DPAPI)** under service `AutoSocialPoster`.
* GET requests return masked values (`••••••••`); cleartext secrets are never exposed to the frontend or written to SQLite.

### 2. Ephemeral Session Token Protection
* The backend generates a cryptographically random 32-byte session token at boot (`secrets.token_hex(32)`).
* The session token is injected directly into `<script>window.__APP_CONFIG__</script>` in the HTML `<head>`.
* All protected endpoints (`/api/*`) require the `X-Session-Token` header, validated with constant-time HMAC comparison (`hmac.compare_digest()`) to prevent timing attacks.
* If a 401 error occurs (e.g. after a backend restart), the client-side API layer automatically calls `/api/bootstrap` to re-synchronize the token and retries the request seamlessly.

### 3. Single-Instance Mutex Lock
* Uses a Win32 Named Mutex (`Global\AutoSocialPoster_SingleInstance_Mutex`) to ensure only one instance of the application runs at any time, avoiding port collisions on `8000` and database locks.
* Launching a second instance automatically focuses the active application window.

### 4. Per-User Windows Profile Isolation
* Application state is stored strictly in `%APPDATA%\AutoSocialPoster\`:
  * Database: `%APPDATA%\AutoSocialPoster\data\social_automation.sqlite3`
  * Execution logs: `%APPDATA%\AutoSocialPoster\logs\social_media_poster.log`
  * Configuration: `%APPDATA%\AutoSocialPoster\config\`
* Multiple Windows users on the same machine operate with completely isolated profiles and credentials.

---

## Core Feature Breakdown

### 1. AI Content Generation (Groq)
* Powered by Groq Cloud (`openai/gpt-oss-120b` or `llama-3.3-70b-versatile`).
* Tailors content simultaneously for both platforms from a single prompt:
  * **LinkedIn:** High-converting hooks, skimmable 1–2 sentence paragraphs, bulleted insights, peer engagement discussion questions, conditional CTA link inclusion, and 3–5 tailored hashtags.
  * **Reddit:** Extracts an authentic discussion header (`Title:`), formats body in clean Markdown, applies practitioner tone without marketing hype, and omits hashtags.
* **Tones Supported:** *Thought Leadership, Conversational, Promotional, Educational, Technical, Storytelling, Controversial / Bold*.
* **Reference Post Learning:** Paste any high-performing post into the *Reference / Inspiration* field to adapt rhythm and structure.

### 2. Post Scheduling & Strict 7-Day Calendar
* **Strict 7-Day Forward Window:** Posts can only be scheduled between **Today** and **Today + 7 Days** (enforced in both the UI and backend).
* **Interactive Calendar (`CalendarPicker.jsx`):**
  * Displays allowed date ranges.
  * Dates beyond +7 days are disabled with a visual lock icon (`Lock`).
  * Click any calendar date to view all queued dispatches for that day.
* **Daily Rate Limit Guard:** Caps daily publications (default: 5 posts/day) to protect accounts from spam detection flags and platform API bans.
* **7-Day Duplicate Content Guard:** Normalizes text and blocks publishing identical content to the same platform within 7 days.
* **Background Scheduler Daemon (`scheduler.py`):**
  * Continuous 60-second polling worker.
  * **Startup Catch-Up:** Overdue posts by $\le$ 2 hours are caught up and dispatched when the app opens; overdue posts by $>$ 2 hours are marked `missed` for explicit user review.

### 3. Multi-Platform Publishing Engine
* **LinkedIn UGC REST API:** Uses the `restli` v2 protocol (`https://api.linkedin.com/rest/posts`) with automatic character escaping for little-text syntax (`[`, `]`, `(`, `)`, `{`, `}`, `<`, `>`, `~`, `_`, `*`, `@`, `|`, `\`).
* **Reddit OAuth API:** Posts directly to target subreddits with automatic title/body parsing.
* **Atomic Idempotency Lock:** SQLite atomic state transitions (`draft/scheduled -> publishing -> published/failed`) prevent duplicate posting.
* **Automatic Rate Limit Backoff:** Handles HTTP 429 responses with exponential backoff and retry.

### 4. Dual-Mode OAuth 2.0 Integration
* **Central Shared App (Default):** Zero configuration required for standard users; developer credentials are maintained on the backend.
* **Custom Developer App Mode:** Power users can enter their own Client ID, Client Secret, User-Agent, and custom Redirect URIs in **Settings > Integrations**.
* **1-Click Loopback Negotiation:** Built-in helper buttons to toggle and copy both `127.0.0.1` and `localhost` callback URIs.
* **1-Click Revert:** Revert to the central shared configuration anytime with a single click.

### 5. Real-Time Terminal & Execution Logs
* Slide-up API Execution Log Drawer (`Terminal` icon) in the header.
* Live tracking of HTTP requests, status codes (`200`, `400`, `429`, `500`), endpoints, and request/response payloads.

---

## Technology Stack

| Layer | Component | Version / Library |
| :--- | :--- | :--- |
| **Frontend UI** | Framework | React 19, Vite 6 |
| | Styling & Icons | Tailwind CSS v4, Lucide React |
| **Desktop Shell** | Native Window | PyWebView 6.2 (WebView2 / WinForms) |
| | Process Control | Win32 Named Mutex (`ctypes`) |
| **Backend API** | ASGI Framework | FastAPI 0.142, Starlette, Uvicorn 0.54 |
| | HTTP Client | HTTPX 0.28 (Async) |
| **Storage & Security** | Local Database | SQLite3 (WAL mode) |
| | Secure Vault | Windows DPAPI via `keyring 25.7` |
| | Auth & Cryptography | PKCE, SHA256, HMAC constant-time digest |
| **Packaging** | Binary Bundler | PyInstaller 6.22 (One-folder mode) |
| | Installer Compiler | Inno Setup 6 (LZMA2/Max Solid Compression) |

---

## Project Structure

```
social-media-posting-automation/
├── .env.example                               # Environment configuration template
├── package.json                               # Frontend dependencies and scripts
├── requirements.txt                           # Python dependencies pinned
├── vite.config.js                             # Vite build configuration (Tailwind v4)
├── AutoSocialPoster.spec                      # PyInstaller build specification
├── build_production.py                        # Automated end-to-end build pipeline
├── installer.iss                              # Inno Setup Windows installer script
├── sign_build.bat                             # Optional code signing batch script
├── index.html                                 # HTML template with dynamic script injection
├── linkedin_reddit_social_media_automation_mvp.tsx  # Master React UI component
│
├── src/
│   ├── main.jsx                               # React bootstrap & session initialization
│   ├── App.jsx                                # Root re-export wrapper
│   ├── CalendarPicker.jsx                     # 7-day window visual calendar picker
│   └── style.css                              # Tailwind CSS rules
│
├── backend/
│   ├── app.py                                 # FastAPI application & route declarations
│   ├── config.py                              # %APPDATA% path resolution & defaults
│   ├── launcher.py                            # PyWebView shell & single-instance lock
│   ├── database/
│   │   └── db.py                              # SQLite connection pool & migrations
│   ├── services/
│   │   ├── ai_service.py                      # Groq AI generation & prompt formatting
│   │   ├── oauth_service.py                   # PKCE OAuth flow & token refresh
│   │   ├── publisher_service.py               # LinkedIn UGC & Reddit API publisher
│   │   └── scheduler.py                       # 60s background queue worker
│   ├── utils/
│   │   ├── license_check.py                   # Checksum verification & activation
│   │   ├── logging_config.py                  # Log rotation & formatting
│   │   ├── numpy_compat.py                    # NumPy compatibility shim
│   │   ├── single_instance.py                 # Windows Mutex lock
│   │   └── vault.py                           # Windows DPAPI vault wrapper
│   └── tests/
│       ├── test_production_verification.py    # 13-point automated integration tests
│       └── test_multi_user_isolation.py       # Multi-user profile isolation test
│
└── installer_dist/                            # Generated Windows installer (.exe)
```

---

## Prerequisites & Development Setup

### System Requirements
* **Operating System:** Windows 10 or Windows 11 (64-bit)
* **Node.js:** v18.0.0 or higher
* **Python:** 3.11.x (64-bit recommended)
* **Inno Setup:** Version 6.x (optional, for compiling the installer)

### 1. Clone & Setup Python Environment
```powershell
# Clone the repository
git clone https://github.com/your-org/social-media-posting-automation.git
cd social-media-posting-automation

# Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Setup Frontend Dependencies
```powershell
# Install Node dependencies
npm install
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Add your Groq API key and optional central OAuth credentials:
```env
PORT=8000
HOST=127.0.0.1
DAILY_POST_CAP=5
GROQ_MODEL=openai/gpt-oss-120b

# Optional: Add Groq API Key (or enter directly in app UI Settings)
GROQ_API_KEY=gsk_your_key_here
```

---

## Running in Development Mode

Run the backend and frontend in separate terminal windows:

### Terminal 1: Backend API (FastAPI)
```powershell
.venv\Scripts\activate
uvicorn app:app --reload --app-dir backend --port 8000
```

### Terminal 2: Frontend (Vite)
```powershell
npm run dev
```

Open your browser to **`http://127.0.0.1:5173`**. The frontend automatically discovers the session token from the backend at `http://127.0.0.1:8000/api/bootstrap`.

---

## Automated Testing & Verification

Run the comprehensive test suite:

```powershell
# Run the 13-point production verification test
python backend/tests/test_production_verification.py

# Run Windows user profile data isolation test
python backend/tests/test_multi_user_isolation.py

# Run security dependency audits
npm audit
pip-audit
```

---

## Production Packaging & Installer Compilation

### One-Step Automated Build Script
To build the complete package (including security audits, React bundle, PyInstaller compilation, and Inno Setup installer):

```powershell
python build_production.py
```

### What this script automates:
1. Runs `npm audit` and `pip-audit` for dependency vulnerabilities.
2. Compiles React frontend via `npm run build` into `dist/`.
3. Runs the backend production test suite.
4. Bundles the application with PyInstaller using `AutoSocialPoster.spec` into `dist/poster-v2/`.
5. Injects essential Windows runtime DLLs (`libcrypto-3-x64.dll`, `libssl-3-x64.dll`, `libffi-8.dll`, `sqlite3.dll`).
6. Compiles `installer.iss` using Inno Setup compiler (`ISCC.exe`) into `installer_dist/poster-v2.exe`.

### Headless Verification Mode
You can verify the packaged executable without opening a UI window:
```powershell
.\dist\poster-v2\poster-v2.exe --check
```
*Returns `[EXE_VERIFICATION_PASS]` and exits with code 0 if all server and SPA endpoints are healthy.*

---

## Configuration & Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the local FastAPI loopback server. |
| `HOST` | `127.0.0.1` | Loopback binding address (locked to local machine). |
| `DAILY_POST_CAP` | `5` | Maximum allowed published posts per platform per day. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq AI model used for draft generation. |
| `LINKEDIN_CLIENT_ID` | `""` | Central developer client ID for LinkedIn. |
| `LINKEDIN_CLIENT_SECRET` | `""` | Central developer client secret for LinkedIn. |
| `LINKEDIN_REDIRECT_URI` | `http://127.0.0.1:8000/auth/linkedin/callback` | Registered LinkedIn OAuth callback URI. |
| `REDDIT_CLIENT_ID` | `""` | Central developer client ID for Reddit. |
| `REDDIT_CLIENT_SECRET` | `""` | Central developer client secret for Reddit. |
| `REDDIT_USER_AGENT` | `AutoSocialPoster/1.0 by u/AutoSocialOfficial` | User agent header for Reddit API requests. |
| `REDDIT_REDIRECT_URI` | `http://127.0.0.1:8000/auth/reddit/callback` | Registered Reddit OAuth callback URI. |

---

## OAuth Developer Portal Checklist

When configuring custom developer credentials in **Settings > Integrations**, ensure your apps have the following configurations:

### LinkedIn Developer Portal
1. Create an app in the [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Under **Products**, add:
   * **Share on LinkedIn**
   * **Sign In with LinkedIn using OpenID Connect**
3. Under **Auth > Authorized redirect URLs**, register **both**:
   * `http://127.0.0.1:8000/auth/linkedin/callback`
   * `http://localhost:8000/auth/linkedin/callback`

### Reddit App Preferences
1. Create an app in [Reddit App Preferences](https://www.reddit.com/prefs/apps).
2. Select type: **installed app** (or **web app**).
3. Set **redirect uri** to **both**:
   * `http://127.0.0.1:8000/auth/reddit/callback`
   * `http://localhost:8000/auth/reddit/callback`

---

## Product Activation & Licensing

AutoSocial Poster includes a built-in cryptographic license verification module (`license_check.py`):
* **Key Format:** `ASPC-XXXX-XXXX-XXXX-XXXX` (checksum-validated via SHA-256).
* **Evaluation / Demo Keys:**
  * `POSTER-V2-PRO-2026`
  * `ASPC-TRIAL-DEMO-2026-B8A1`
  * `ASPC-DEV-PASS-FREE-9F2C`
* License keys are entered in the installer or under **Settings > License & Activation** in the app. Activated keys are stored encrypted in the Windows DPAPI Vault.

---

## License

Proprietary Software. All rights reserved &copy; AutoSocial Technologies.
