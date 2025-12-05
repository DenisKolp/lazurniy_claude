#!/usr/bin/env python3
"""
Test script to verify member registry update functionality
"""
import asyncio
from services.sheets_service import SheetsService


async def test_registry_update():
    """Test updating member registry multiple times"""
    print("=" * 60)
    print("Testing Member Registry Updates")
    print("=" * 60)
    print()

    service = SheetsService()

    # Test 1: Create with one member
    print("1. Creating registry with one member...")
    members_1 = [
        {
            'full_name': 'Иванов Иван Иванович',
            'username': 'ivanov',
            'phone_number': '+79991234567',
            'address': 'ул. Тестовая, д. 1',
            'verified_at': '05.12.2025 12:00'
        }
    ]

    url_1 = await service.export_members_registry(members_1)
    if url_1:
        print(f"✅ Registry created: {url_1}")
    else:
        print("❌ Failed to create registry")
        return False

    print()

    # Test 2: Update with two members
    print("2. Updating registry with two members...")
    members_2 = [
        {
            'full_name': 'Иванов Иван Иванович',
            'username': 'ivanov',
            'phone_number': '+79991234567',
            'address': 'ул. Тестовая, д. 1',
            'verified_at': '05.12.2025 12:00'
        },
        {
            'full_name': 'Петров Петр Петрович',
            'username': 'petrov',
            'phone_number': '+79991234568',
            'address': 'ул. Тестовая, д. 2',
            'verified_at': '05.12.2025 13:00'
        }
    ]

    url_2 = await service.export_members_registry(members_2)
    if url_2:
        print(f"✅ Registry updated: {url_2}")
    else:
        print("❌ Failed to update registry")
        return False

    print()

    # Test 3: Update with three members
    print("3. Updating registry with three members...")
    members_3 = [
        {
            'full_name': 'Иванов Иван Иванович',
            'username': 'ivanov',
            'phone_number': '+79991234567',
            'address': 'ул. Тестовая, д. 1',
            'verified_at': '05.12.2025 12:00'
        },
        {
            'full_name': 'Петров Петр Петрович',
            'username': 'petrov',
            'phone_number': '+79991234568',
            'address': 'ул. Тестовая, д. 2',
            'verified_at': '05.12.2025 13:00'
        },
        {
            'full_name': 'Сидоров Сидор Сидорович',
            'username': 'sidorov',
            'phone_number': '+79991234569',
            'address': 'ул. Тестовая, д. 3',
            'verified_at': '05.12.2025 14:00'
        }
    ]

    url_3 = await service.export_members_registry(members_3)
    if url_3:
        print(f"✅ Registry updated: {url_3}")
    else:
        print("❌ Failed to update registry")
        return False

    print()
    print("=" * 60)
    print("✅ All updates completed successfully!")
    print("=" * 60)
    print()
    print("Check the registry spreadsheet to verify all members are listed:")
    print(url_3)
    print()

    return True


if __name__ == '__main__':
    success = asyncio.run(test_registry_update())
    exit(0 if success else 1)
