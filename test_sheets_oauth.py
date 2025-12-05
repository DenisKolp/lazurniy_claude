#!/usr/bin/env python3
"""
Test script to verify Google Sheets OAuth2 integration works correctly.
"""
import asyncio
from datetime import datetime, timedelta
from services.sheets_service import SheetsService


async def test_oauth_sheets():
    """Test creating a spreadsheet with OAuth2 credentials."""
    print("=" * 60)
    print("Testing Google Sheets with OAuth2")
    print("=" * 60)
    print()

    # Initialize service
    print("1. Initializing SheetsService...")
    service = SheetsService()

    if not service.client:
        print("❌ Failed to initialize service!")
        return False

    auth_method = "OAuth2" if service.use_oauth else "Service Account"
    print(f"✅ Service initialized with {auth_method}")
    print(f"   Folder ID: {service.folder_id}")
    print()

    # Test 1: Create voting results spreadsheet
    print("2. Testing voting results export...")
    try:
        url = await service.export_voting_results(
            voting_id=1000,
            voting_title="Тестовое голосование OAuth2",
            voting_description="Проверка работы OAuth2 аутентификации с Google Sheets API",
            options=["За", "Против", "Воздержался"],
            results={0: 15, 1: 3, 2: 2},
            total_votes=20,
            created_at=datetime.now() - timedelta(days=7),
            ends_at=datetime.now()
        )

        if url:
            print(f"✅ Voting spreadsheet created!")
            print(f"   URL: {url}")
        else:
            print("❌ Failed to create voting spreadsheet")
            return False

    except Exception as e:
        print(f"❌ Error creating voting spreadsheet: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # Test 2: Create members registry spreadsheet
    print("3. Testing members registry export...")
    try:
        test_members = [
            {
                'full_name': 'Иванов Иван Иванович',
                'username': 'ivanov',
                'phone_number': '+79991234567',
                'address': 'ул. Тестовая, д. 1',
                'verified_at': '2025-12-05 12:00:00'
            },
            {
                'full_name': 'Петров Петр Петрович',
                'username': 'petrov',
                'phone_number': '+79991234568',
                'address': 'ул. Тестовая, д. 2',
                'verified_at': '2025-12-05 13:00:00'
            }
        ]

        url = await service.export_members_registry(
            members=test_members,
            spreadsheet_name="Тест: Реестр членов ассоциации"
        )

        if url:
            print(f"✅ Registry spreadsheet created!")
            print(f"   URL: {url}")
        else:
            print("❌ Failed to create registry spreadsheet")
            return False

    except Exception as e:
        print(f"❌ Error creating registry spreadsheet: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print()
    print("Check your Google Drive folder:")
    if service.folder_id:
        print(f"https://drive.google.com/drive/folders/{service.folder_id}")
    print()

    return True


if __name__ == '__main__':
    success = asyncio.run(test_oauth_sheets())
    exit(0 if success else 1)
