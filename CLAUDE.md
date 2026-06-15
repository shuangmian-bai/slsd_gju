# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Does

Automates course evaluation (评教) for 湖南水利水电职业技术学院. Logs into the SSO system, obtains session cookies via CAS protocol, then submits full-mark evaluations for all pending courses.

## Commands

```bash
# Install dependencies
pip install requests beautifulsoup4 pycryptodome ddddocr

# Run full evaluation (with Clash proxy)
python3 pingjiao.py <student_id> <password> --proxy http://127.0.0.1:7890

# SSO login only (returns JSON with cookies)
python3 login.py <student_id> <password> --proxy http://127.0.0.1:7890
```

## Architecture

**login.py** — SSO authentication module. Reverse-engineered from the Angular frontend at `sso.hnslsdxy.com`. Key details:
- Password encrypted with AES-128-ECB (key = base64-decoded `login-croypto` from page HTML, 16 bytes)
- Captcha handled via `ddddocr` OCR with auto-retry (max 3 attempts)
- Returns `{"success", "cookies", "message"}` dict
- `cookies` dict contains: `SESSION`, `SOURCEID_TGC`, `__jsluid_s`, `rg_objectid`

**pingjiao.py** — Evaluation orchestrator. Imports `login()` from `login.py`, then:
1. Calls `login()` to get SSO cookies
2. `create_session()` performs CAS redirect chain: `assess.hnslsdxy.com` → `sso.hnslsdxy.com` (with ticket) → back to assess, yielding `sessionid` + `csrftoken` cookies
3. `get_assessments()` / `save_assessment()` call the assess API at `assess.hnslsdxy.com`

**main.py** — Legacy version (reads cookies from curl dump file). Superseded by `pingjiao.py`.

## Key Technical Details

- The SSO login form POSTs to `/login` with `application/x-www-form-urlencoded` (not JSON)
- The `login-croypto` value is a base64 string that decodes to 16 bytes — used directly as AES key (not UTF-8 bytes)
- CSRF headers (`Csrf-Key` / `Csrf-Value`) are static values extracted from the frontend JS
- Assessment service requires CAS ticket validation — SSO cookies alone are insufficient
- The assess API requires `X-CSRFToken` header from the `csrftoken` cookie

## External Services

| Domain | Role |
|--------|------|
| `sso.hnslsdxy.com` | SSO authentication (CAS server) |
| `portal.hnslsdxy.com` | Portal (ticket validation redirect) |
| `assess.hnslsdxy.com` | Course evaluation API |
