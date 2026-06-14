# Security Model — AI Home Assistant

## Overview

This document defines the security architecture for protecting family content stored in Google Drive and accessed through the AI Home Assistant app.

---

## 1. Authentication

### OAuth 2.0 (Google Identity)
- All Google Drive access uses **OAuth 2.0** — no service account keys, no hardcoded credentials.
- Users sign in with their personal Google account via the standard Google Sign-In SDK on Android.
- A **refresh token** is obtained after first login and stored securely (see Token Storage below).

### Token Storage on Android
- Refresh tokens are stored in the **Android Keystore** (hardware-backed secure enclave).
- Never use `SharedPreferences`, plain files, or SQLite for tokens.
- Access tokens (short-lived, ~1 hour) are held in memory only — never persisted to disk.

```
Android Keystore
  └── AI-HomeAssistant-OAuth-RefreshToken  (AES-256 encrypted, hardware-backed)
```

---

## 2. Google Drive Access Control

### Folder Permissions
- The family Drive folder is shared **only with specific family Google accounts** — not "Anyone with the link".
- Remove any public sharing links from the storage folder.
- Use **folder-level sharing**, not individual file sharing, for easier management.

### OAuth Scopes (Least Privilege)
Request only the minimum scopes needed:

| Scope | Why |
|---|---|
| `https://www.googleapis.com/auth/drive.file` | Access only files created/opened by this app |
| `https://www.googleapis.com/auth/drive.readonly` | Read-only access if writing is not needed |

**Never request** `https://www.googleapis.com/auth/drive` (full Drive access) unless absolutely required.

---

## 3. MCP Server Security

The MCP server acts as the bridge between the AI agent and Google Drive.

- Run the MCP server **locally on your home network** — never expose it to the public internet.
- The MCP server must **never log file contents** — only log metadata (file IDs, operation type, timestamps).
- All credentials passed to the MCP server come from **environment variables**, not config files checked into git.
- Communication between the Android app and local MCP server uses **HTTPS with a self-signed cert** (or mTLS for stronger security).

### Environment Variables (never commit these)
```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...
DRIVE_FOLDER_ID=1AY77PvZPwXZmnhI8egyLbIV7zK6_eAyh
```

---

## 4. What Must Never Go in Git

The following are listed in `.gitignore` and must never be committed:

```
.env
*.env.*
credentials/
client_secret.json
token.json
*.keystore
*.jks
google-services.json     # contains Firebase/Google API keys
local.properties
```

---

## 5. Data in Transit

- All communication with Google APIs is over **HTTPS/TLS** (enforced by Google).
- Local network traffic between Android app and MCP server: use **HTTPS** (even on local network).
- No family content is ever sent to third-party services without explicit user consent.

---

## 6. Data at Rest

- Files remain in **Google Drive** — the app does not download and cache family files locally (except temporary thumbnails, which are cleared on app close).
- Any local AI inference cache must be stored in Android's **internal storage** (`context.filesDir`), not external storage.

---

## 7. Family Member Access

| Role | Access Level |
|---|---|
| Admin (owner) | Full read/write, manage sharing |
| Family member | Read/write to shared folder only |
| Guest | No access (not supported in v1) |

---

## 8. Threat Model

| Threat | Mitigation |
|---|---|
| Stolen device | Android Keystore tokens require device unlock; remote revoke via Google account |
| Leaked repo | `.gitignore` blocks credentials; no secrets in code |
| MCP server exposed | Run on local network only; no public port forwarding |
| Over-privileged scopes | Use `drive.file` scope, not full `drive` |
| Public Drive folder | Share only with named family accounts |

---

## 9. Incident Response

If credentials are compromised:
1. Revoke OAuth tokens immediately at [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
2. Rotate `GOOGLE_CLIENT_SECRET` in Google Cloud Console
3. Re-authenticate all family devices
4. Review Drive folder sharing and audit access logs in Google Admin
