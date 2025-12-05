#!/usr/bin/env python3
"""
Script to generate OAuth2 token for Google Sheets API using user credentials.
This allows the bot to create files in your personal Google Drive.

Usage:
1. Create OAuth 2.0 credentials in Google Cloud Console:
   - Go to https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download the credentials JSON file as 'oauth_credentials.json'

2. Run this script: python get_oauth_token.py
3. Follow the browser prompts to authorize the application
4. The script will save 'token.json' which will be used by the bot
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required for Google Sheets and Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def get_credentials():
    """Get or refresh OAuth2 credentials."""
    creds = None

    # Check if token already exists
    if os.path.exists('token.json'):
        print("Loading existing token...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists('oauth_credentials.json'):
                print("\n❌ ERROR: oauth_credentials.json not found!")
                print("\nPlease create OAuth 2.0 credentials:")
                print("1. Go to https://console.cloud.google.com/apis/credentials")
                print("2. Create credentials → OAuth 2.0 Client ID")
                print("3. Application type: Desktop app")
                print("4. Download the JSON file and save it as 'oauth_credentials.json'")
                print("5. Make sure Google Sheets API and Google Drive API are enabled")
                return None

            print("\nStarting OAuth2 flow...")
            print("A browser window will open for authorization.")
            flow = InstalledAppFlow.from_client_secrets_file(
                'oauth_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ Token saved to token.json")

    return creds

def main():
    """Main function to get and display OAuth2 token."""
    print("=" * 60)
    print("Google Sheets OAuth2 Token Generator")
    print("=" * 60)
    print()

    creds = get_credentials()

    if creds:
        print("\n✅ SUCCESS! OAuth2 credentials obtained.")
        print("\nCredentials info:")
        print(f"  - Token: {creds.token[:20]}...") if creds.token else None
        print(f"  - Refresh token: {'Available' if creds.refresh_token else 'Not available'}")
        print(f"  - Scopes: {', '.join(SCOPES)}")
        print("\n📄 Token saved to: token.json")
        print("\nYou can now use this token in your bot.")
        print("Copy token.json to your Docker container or mount it as a volume.")

        # Display token info
        with open('token.json', 'r') as f:
            token_data = json.load(f)
            print("\nToken file contents (first 500 chars):")
            print(json.dumps(token_data, indent=2)[:500] + "...")
    else:
        print("\n❌ Failed to obtain credentials.")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
