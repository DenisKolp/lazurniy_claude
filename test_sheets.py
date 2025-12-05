"""
Test Google Sheets integration
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 50)
print("Testing Google Sheets Integration")
print("=" * 50)

# Test 1: Check if libraries are installed
print("\n1. Checking if gspread and oauth2client are installed...")
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    print("✅ Libraries installed")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTo install, run:")
    print("pip install gspread oauth2client")
    exit(1)

# Test 2: Check if credentials file exists
print("\n2. Checking credentials.json file...")
import os
if os.path.exists('credentials.json'):
    print("✅ credentials.json exists")
    # Check file size
    size = os.path.getsize('credentials.json')
    print(f"   File size: {size} bytes")
else:
    print("❌ credentials.json not found")
    exit(1)

# Test 3: Try to initialize client
print("\n3. Initializing Google Sheets client...")
try:
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json',
        scope
    )
    client = gspread.authorize(creds)
    print("✅ Client initialized successfully")

    # Get service account email
    with open('credentials.json', 'r') as f:
        import json
        creds_data = json.load(f)
        email = creds_data.get('client_email', 'N/A')
        print(f"   Service Account: {email}")

except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    exit(1)

# Test 4: Try to create a test spreadsheet
print("\n4. Creating test spreadsheet...")
try:
    test_sheet = client.create("TEST - Lazurny Bot Registry")
    print(f"✅ Test spreadsheet created: {test_sheet.url}")

    # Add some data
    worksheet = test_sheet.sheet1
    worksheet.update('A1', [
        ['Test Registry'],
        [''],
        ['Name', 'Status'],
        ['Test User', 'OK']
    ])
    print("✅ Data added to spreadsheet")

    # Make it public
    test_sheet.share('', perm_type='anyone', role='reader')
    print("✅ Spreadsheet made public")

    print(f"\n🎉 SUCCESS! Google Sheets is working!")
    print(f"📊 Test spreadsheet URL: {test_sheet.url}")
    print(f"\nYou can now delete this test spreadsheet from Google Drive.")

except Exception as e:
    print(f"❌ Failed to create spreadsheet: {e}")
    print("\nPossible issues:")
    print("- Service account doesn't have Drive API enabled")
    print("- Credentials file is invalid")
    print("- Network connection problem")
    exit(1)

print("\n" + "=" * 50)
print("All tests passed! ✅")
print("=" * 50)
