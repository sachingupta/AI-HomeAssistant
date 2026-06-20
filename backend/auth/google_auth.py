"""
Run this script ONCE to complete the Google OAuth flow and get a refresh token.
The refresh token is saved to .env as GOOGLE_REFRESH_TOKEN and used by the
Drive client on every subsequent run — no browser interaction needed after this.

Usage:
    cd AI-HomeAssistant
    python -m backend.auth.google_auth
"""

import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def main():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env first.")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080/oauth/callback"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(port=8080, prompt="consent")

    print("\n✓ Authentication successful!\n")
    print("Add this line to your .env file:\n")
    print(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}\n")

    # Optionally write directly to .env if it exists
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()

        if "GOOGLE_REFRESH_TOKEN=" in content:
            lines = content.splitlines()
            lines = [
                f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}"
                if l.startswith("GOOGLE_REFRESH_TOKEN=")
                else l
                for l in lines
            ]
            updated = "\n".join(lines) + "\n"
        else:
            updated = content.rstrip("\n") + f"\nGOOGLE_REFRESH_TOKEN={credentials.refresh_token}\n"

        with open(env_path, "w") as f:
            f.write(updated)
        print(f"✓ Automatically written to {env_path}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
