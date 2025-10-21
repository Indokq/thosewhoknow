# Warp Account Manager - Project Documentation

## 1. Project Overview
- Purpose: Cross-platform desktop tool to manage multiple Warp.dev accounts, automate token handling, and enable seamless account switching while monitoring usage limits and ban status.
- Goals:
  - Manage and switch between multiple accounts quickly
  - Intercept Warp.dev traffic to inject valid tokens per active account
  - Show request limit usage and health (healthy/unhealthy/banned)
  - Provide Chrome extension bridge for automated account ingestion
  - Offer one-click certificate setup and system proxy configuration

## 2. Technology Stack
- Language: Python 3.8+
- GUI: PyQt5
- Proxy/Interception: mitmproxy (mitmdump)
- Storage: SQLite (`accounts.db`)
- Browser Integration: Chrome Extension (Manifest v3)
- Networking: requests, urllib3
- OS Integration:
  - Windows: winreg, certutil, registry proxy settings
  - macOS: security/Keychain integration, PAC support
  - Linux: manual certificate trust

Dependencies (requirements.txt)
- PyQt5, requests, mitmproxy, psutil

## 3. Architecture
- Current Modules:
  - `warp_account_manager.py`: Main application (UI + orchestration + business logic)
  - `warp_proxy_script.py`: mitmproxy script to modify Warp.dev requests and headers
  - `warp_bridge_server.py`: Local HTTP bridge for Chrome extension to add accounts
  - `languages.py`: i18n (TR/EN) utilities
  - `windows_bridge_config.py`, `macos_bridge_config.py`: Platform adapters
  - `chrome-extension/*`: Manifest v3 background/content scripts and config
- Key Flows:
  - Account Storage: SQLite `accounts` table stores `account_data` JSON and health/limit info
  - Active Account: `proxy_settings.active_account` determines which token to inject
  - Token Lifecycle: Automatic refresh via Google Secure Token endpoint before expiry
  - Limit Fetch: GraphQL v2 `GetRequestLimitInfo` to display usage
  - User Settings: GraphQL v2 `GetUpdatedCloudObjects` cached in `user_settings.json`
  - Ban Detection: 403 on `/ai/multi-agent` marks account as banned
  - Bridge: Chrome extension posts account JSON to local server (port 8765)
- Notable Headers/Flags:
  - `X-Warp-Manager-Request: true` to avoid self-interception
  - Randomized `X-Warp-Experiment-Id` for privacy
  - RudderStack traffic blocked

Target Architecture (planned refactor)
- Core application (entry)
- UI layer (PyQt widgets, views)
- Services: ProxyService, AccountService, ApiService, CertificateService
- Data layer: Repositories (SQLite), models
- Integration: Bridge server, extension protocol
- Config: Centralized settings/constants

## 4. Code Standards
- Python: snake_case for functions/variables, PascalCase for classes
- Function size target: <40 lines; File size target: <300 lines
- Replace magic numbers with named constants
- Error handling with explicit exceptions; avoid bare `except:`
- Logging: structured logging (planned); avoid print in production paths
- Internationalization via `languages.py`; default EN fallback

## 5. Technical Constraints
- Runs on Windows, macOS, Linux with platform-specific certificate and proxy setup
- HTTPS interception requires trusting mitmproxy CA certificate
- Localhost-only bridge (port 8765); cross-origin restricted to extension
- Requests to Google Secure Token and Warp GraphQL must bypass proxy when refreshing tokens
- Headless proxy operation is desirable; debug mode optional

## 6. Testing Strategy
- Unit tests for:
  - Token refresh logic
  - DB repository (CRUD, migrations)
  - Header injection and domain filtering
- Integration tests for:
  - Bridge POST `/add-account`
  - Proxy script flows with mitmdump in test mode
  - Certificate detection/installation (mocked)
- End-to-end smoke:
  - Start app headless proxy, set active account, verify modified request
- Quality gates: static analysis (flake8/ruff), type hints where practical, CI matrix for OSes

## 7. Development Workflow
- Branches: `main`, `feature/*`, `fix/*`, `refactor/*`
- Conventional Commits: feat, fix, refactor, docs, test, chore
- PR checklist:
  - Lint/test pass
  - Security implications reviewed (token handling, cert trust)
  - Docs updated (OpenSpec/README)

## 8. Domain Knowledge
- Warp.dev GraphQL endpoints used for limits and cloud objects
- Firebase STS refresh via `securetoken.googleapis.com`
- `X-Warp-Client-Version` and OS headers expected by Warp backend
- RudderStack analytics calls blocked for privacy/noise reduction
- IndexedDB (firebaseLocalStorageDb) used by web app; extension extracts account JSON

## 9. Technical Debt & Roadmap
- High priority:
  - Decompose `warp_account_manager.py` into modules (UI/services/data)
  - Implement fully headless proxy mode with robust logging
  - Centralize config and constants; remove hardcoded values
- Medium priority:
  - Introduce repository pattern and connection management for SQLite
  - Replace print with logging + rotating file handlers
  - Add automated tests and CI
- Low priority:
  - Expand i18n coverage; add language toggle
  - Improve macOS/Linux certificate flows

## 10. External Dependencies
- Warp.dev API (GraphQL v2)
- Google Secure Token (Firebase)
- Chrome browser (for extension-based ingestion)
- OS certificate/keychain stores
