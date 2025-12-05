"""
Google Sheets integration service
"""
import json
import logging
import os
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Flag to check if gspread is available
GSPREAD_AVAILABLE = False
try:
    import gspread
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials as OAuth2Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    logger.warning("gspread or google-auth not installed. Google Sheets integration disabled.")


class SheetsService:
    """Service for exporting voting results to Google Sheets"""

    def __init__(self, credentials_path: Optional[str] = None, folder_id: Optional[str] = None, use_oauth: bool = None):
        """
        Initialize Google Sheets service

        Args:
            credentials_path: Path to credentials JSON file (service account or OAuth token)
            folder_id: Google Drive folder ID where spreadsheets will be created
            use_oauth: If True, use OAuth2 token.json; if False, use service account credentials.json
                      If None, auto-detect based on available files.
        """
        # Determine authentication method
        if use_oauth is None:
            # Auto-detect: prefer OAuth token if available
            use_oauth = os.path.exists("token.json")

        self.use_oauth = use_oauth
        self.credentials_path = credentials_path or ("token.json" if use_oauth else "credentials.json")
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.client = None

        if GSPREAD_AVAILABLE and self._initialize_client():
            auth_method = "OAuth2" if self.use_oauth else "Service Account"
            logger.info(f"Google Sheets service initialized with {auth_method} (folder_id: {self.folder_id})")
        else:
            logger.warning("Google Sheets service not available")

    def _initialize_client(self) -> bool:
        """Initialize gspread client with credentials"""
        try:
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]

            if self.use_oauth:
                # Use OAuth2 token from user account
                logger.info(f"Loading OAuth2 credentials from {self.credentials_path}")
                creds = OAuth2Credentials.from_authorized_user_file(
                    self.credentials_path,
                    scopes=scope
                )
            else:
                # Use service account credentials
                logger.info(f"Loading Service Account credentials from {self.credentials_path}")
                creds = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path,
                    scopes=scope
                )

            self.client = gspread.authorize(creds)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            return False

    async def export_voting_results(
        self,
        voting_id: int,
        voting_title: str,
        voting_description: str,
        options: List[str],
        results: Dict[int, int],
        total_votes: int,
        created_at: datetime,
        ends_at: datetime,
        spreadsheet_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Export voting results to Google Sheets

        Args:
            voting_id: Voting ID
            voting_title: Voting title
            voting_description: Voting description
            options: List of voting options
            results: Dictionary mapping option index to vote count
            total_votes: Total number of votes
            created_at: When voting was created
            ends_at: When voting ended
            spreadsheet_name: Optional custom spreadsheet name

        Returns:
            URL to the created spreadsheet or None if failed
        """
        if not GSPREAD_AVAILABLE or not self.client:
            logger.warning("Google Sheets not available, skipping export")
            return None

        try:
            # Create or open spreadsheet
            sheet_name = spreadsheet_name or f"Голосование #{voting_id}: {voting_title}"

            try:
                spreadsheet = self.client.create(sheet_name, folder_id=self.folder_id)
                logger.info(f"Created new spreadsheet: {sheet_name} in folder {self.folder_id}")
            except Exception as e:
                logger.error(f"Failed to create spreadsheet: {e}")
                return None

            # Get first worksheet
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Результаты")

            # Prepare data
            data = [
                ["Голосование - Результаты"],
                [""],
                ["Название:", voting_title],
                ["Описание:", voting_description],
                ["ID голосования:", str(voting_id)],
                ["Создано:", created_at.strftime("%d.%m.%Y %H:%M")],
                ["Завершено:", ends_at.strftime("%d.%m.%Y %H:%M")],
                ["Всего голосов:", str(total_votes)],
                [""],
                ["Вариант ответа", "Количество голосов", "Процент"]
            ]

            # Add results for each option
            for i, option in enumerate(options):
                votes = results.get(i, 0)
                percent = (votes / total_votes * 100) if total_votes > 0 else 0
                data.append([
                    option,
                    str(votes),
                    f"{percent:.1f}%"
                ])

            # Add footer
            data.append([""])
            data.append([
                f"Экспортировано: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}"
            ])

            # Update worksheet with data
            worksheet.update('A1', data)

            # Format the spreadsheet
            self._format_worksheet(worksheet, len(options))

            # Make spreadsheet publicly readable
            try:
                spreadsheet.share('', perm_type='anyone', role='reader')
                logger.info(f"Made spreadsheet publicly readable")
            except Exception as e:
                logger.warning(f"Failed to make spreadsheet public: {e}")

            # Return spreadsheet URL
            url = spreadsheet.url
            logger.info(f"Voting results exported to: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to export voting results: {e}")
            return None

    def _format_worksheet(self, worksheet, num_options: int):
        """Apply formatting to the worksheet"""
        try:
            # Format header (row 1)
            worksheet.format('A1:C1', {
                'textFormat': {'bold': True, 'fontSize': 14},
                'horizontalAlignment': 'CENTER',
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9}
            })

            # Format data headers (row 10)
            worksheet.format('A10:C10', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })

            # Format info section
            worksheet.format('A3:A8', {
                'textFormat': {'bold': True}
            })

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 2)

        except Exception as e:
            logger.warning(f"Failed to format worksheet: {e}")

    async def get_spreadsheet_url(self, spreadsheet_id: str) -> Optional[str]:
        """Get URL for an existing spreadsheet"""
        if not GSPREAD_AVAILABLE or not self.client:
            return None

        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            return spreadsheet.url
        except Exception as e:
            logger.error(f"Failed to get spreadsheet URL: {e}")
            return None

    async def export_members_registry(
        self,
        members: List[Dict],
        spreadsheet_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Export members registry to Google Sheets

        Args:
            members: List of member dictionaries with user data
            spreadsheet_name: Optional custom spreadsheet name

        Returns:
            URL to the created/updated spreadsheet or None if failed
        """
        if not GSPREAD_AVAILABLE or not self.client:
            logger.warning("Google Sheets not available, skipping export")
            return None

        try:
            # Create or open spreadsheet
            sheet_name = spreadsheet_name or "Реестр членов ассоциации КП Лазурный"

            try:
                # Try to open existing spreadsheet in the folder
                if self.folder_id:
                    # Search for the spreadsheet in the specific folder
                    files = self.client.list_spreadsheet_files(folder_id=self.folder_id)
                    matching_file = next((f for f in files if f['name'] == sheet_name), None)
                    if matching_file:
                        spreadsheet = self.client.open_by_key(matching_file['id'])
                        logger.info(f"Opened existing spreadsheet: {sheet_name}")
                        worksheet = spreadsheet.sheet1
                        worksheet.clear()
                    else:
                        raise FileNotFoundError("Spreadsheet not found in folder")
                else:
                    spreadsheet = self.client.open(sheet_name)
                    logger.info(f"Opened existing spreadsheet: {sheet_name}")
                    worksheet = spreadsheet.sheet1
                    worksheet.clear()
            except:
                # Create new if doesn't exist
                spreadsheet = self.client.create(sheet_name, folder_id=self.folder_id)
                logger.info(f"Created new spreadsheet: {sheet_name} in folder {self.folder_id}")
                worksheet = spreadsheet.sheet1

            worksheet.update_title("Реестр")

            # Prepare header
            data = [
                ["Реестр членов ассоциации КП 'Лазурный'"],
                [""],
                ["№", "ФИО", "Username", "Телефон", "Адрес участка", "Дата верификации"]
            ]

            # Add members data
            for idx, member in enumerate(members, 1):
                data.append([
                    str(idx),
                    member.get('full_name', 'Не указано'),
                    f"@{member.get('username', 'N/A')}",
                    member.get('phone_number', 'Не указан'),
                    member.get('address', 'Не указан'),
                    member.get('verified_at', 'Не указана')
                ])

            # Add footer
            data.append([""])
            data.append([
                f"Всего членов: {len(members)}",
                "",
                "",
                "",
                "",
                f"Обновлено: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}"
            ])

            # Update worksheet with data
            worksheet.update('A1', data)

            # Format the spreadsheet
            self._format_registry_worksheet(worksheet, len(members))

            # Make spreadsheet publicly readable
            try:
                spreadsheet.share('', perm_type='anyone', role='reader')
                logger.info(f"Made spreadsheet publicly readable")
            except Exception as e:
                logger.warning(f"Failed to make spreadsheet public: {e}")

            # Return spreadsheet URL
            url = spreadsheet.url
            logger.info(f"Members registry exported to: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to export members registry: {e}")
            return None

    def _format_registry_worksheet(self, worksheet, num_members: int):
        """Apply formatting to the registry worksheet"""
        try:
            # Format title (row 1)
            worksheet.format('A1:F1', {
                'textFormat': {'bold': True, 'fontSize': 14},
                'horizontalAlignment': 'CENTER',
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9}
            })

            # Format header (row 3)
            worksheet.format('A3:F3', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'horizontalAlignment': 'CENTER'
            })

            # Format data rows with zebra striping
            for i in range(4, 4 + num_members):
                if i % 2 == 0:
                    worksheet.format(f'A{i}:F{i}', {
                        'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}
                    })

            # Auto-resize columns
            worksheet.columns_auto_resize(0, 5)

        except Exception as e:
            logger.warning(f"Failed to format registry worksheet: {e}")


# Global instance
sheets_service = SheetsService()
