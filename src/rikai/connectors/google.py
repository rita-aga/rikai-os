"""
Google Docs Connector

Ingests Google Docs and Drive files into Umi:
- Google Docs as documents
- Shared folders
- Scheduled sync
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from pathlib import Path
from typing import Any

import httpx

from rikai.core.models import DocumentSource, EntityType
from rikai.connectors.base import (
    APIConnector,
    ConnectorConfig,
    ConnectorMode,
    ConnectorStatus,
    IngestResult,
)

logger = logging.getLogger(__name__)


@dataclass
class GoogleConnectorConfig(ConnectorConfig):
    """Configuration for the Google connector."""
    credentials_path: str = "~/.rikai/google_credentials.json"
    token_path: str = "~/.rikai/google_token.json"
    folder_ids: list[str] = field(default_factory=list)  # Specific folders to sync
    include_shared: bool = True
    file_types: list[str] = field(default_factory=lambda: [
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "text/plain",
        "text/markdown",
    ])


@dataclass
class GoogleFile:
    """A Google Drive file."""
    id: str
    name: str
    mime_type: str
    modified_time: datetime | None = None
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class GoogleConnector(APIConnector):
    """
    Connector for Google Docs and Drive.

    Requires OAuth2 credentials from Google Cloud Console.
    """

    name = "google"
    mode = ConnectorMode.PULL
    description = "Google Docs/Drive connector"

    # Google API endpoints
    DRIVE_API = "https://www.googleapis.com/drive/v3"
    DOCS_API = "https://docs.googleapis.com/v1"

    def __init__(self, config: GoogleConnectorConfig | None = None) -> None:
        super().__init__(config or GoogleConnectorConfig())
        self._config: GoogleConnectorConfig
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None

    async def setup(self) -> None:
        """Set up the Google connector."""
        self._client = httpx.AsyncClient(timeout=30.0)
        self._status = ConnectorStatus.IDLE

    async def authenticate(self) -> bool:
        """
        Authenticate with Google OAuth2.

        Requires credentials.json from Google Cloud Console.
        """
        token_path = Path(self._config.token_path).expanduser()

        if token_path.exists():
            try:
                with open(token_path) as f:
                    token_data = json.load(f)

                # Check if token is expired
                expiry = token_data.get("expiry")
                if expiry:
                    expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                    if expiry_dt > datetime.now(expiry_dt.tzinfo):
                        self._access_token = token_data.get("access_token")
                        return True

                # Try to refresh
                if "refresh_token" in token_data:
                    refreshed = await self._refresh_token(token_data)
                    if refreshed:
                        return True

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse token file: {e}")

        # Need to do OAuth flow
        self._status = ConnectorStatus.ERROR
        return False

    async def _refresh_token(self, token_data: dict) -> bool:
        """Refresh an expired access token."""
        credentials_path = Path(self._config.credentials_path).expanduser()

        if not credentials_path.exists():
            return False

        try:
            with open(credentials_path) as f:
                creds = json.load(f)

            client_id = creds.get("installed", {}).get("client_id")
            client_secret = creds.get("installed", {}).get("client_secret")
            refresh_token = token_data.get("refresh_token")

            if not all([client_id, client_secret, refresh_token]):
                return False

            response = await self._client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 200:
                new_token = response.json()
                self._access_token = new_token["access_token"]

                # Save updated token
                token_data["access_token"] = new_token["access_token"]
                if "expires_in" in new_token:
                    expiry = datetime.now(UTC) + timedelta(seconds=new_token["expires_in"])
                    token_data["expiry"] = expiry.isoformat() + "Z"

                token_path = Path(self._config.token_path).expanduser()
                with open(token_path, "w") as f:
                    json.dump(token_data, f)

                return True

        except Exception as e:
            logger.warning(f"Failed to refresh Google OAuth token: {e}")

        return False

    async def fetch_items(
        self,
        cursor: str | None = None,
        limit: int = 100,
    ) -> tuple[list[Any], str | None]:
        """Fetch files from Google Drive."""
        if not self._access_token or not self._client:
            return [], None

        try:
            # Build query
            query_parts = []

            # Filter by mime types
            mime_filters = " or ".join(
                f"mimeType='{mt}'" for mt in self._config.file_types
            )
            query_parts.append(f"({mime_filters})")

            # Filter by folders if specified
            if self._config.folder_ids:
                folder_filter = " or ".join(
                    f"'{fid}' in parents" for fid in self._config.folder_ids
                )
                query_parts.append(f"({folder_filter})")

            # Exclude trashed
            query_parts.append("trashed=false")

            query = " and ".join(query_parts)

            params = {
                "q": query,
                "pageSize": min(limit, 100),
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,owners,shared)",
                "orderBy": "modifiedTime desc",
            }

            if cursor:
                params["pageToken"] = cursor

            response = await self._client.get(
                f"{self.DRIVE_API}/files",
                params=params,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )

            if response.status_code != 200:
                return [], None

            data = response.json()
            files = data.get("files", [])
            next_cursor = data.get("nextPageToken")

            return files, next_cursor

        except Exception as e:
            logger.warning(f"Failed to list files from Google Drive: {e}")
            return [], None

    async def sync(self) -> IngestResult:
        """Sync Google Drive files."""
        if not self._umi:
            return IngestResult(success=False, errors=["Not initialized"])

        # Authenticate first
        if not await self.authenticate():
            return IngestResult(
                success=False,
                errors=["Authentication failed. Run 'rikai google auth' first."],
            )

        self._status = ConnectorStatus.RUNNING
        result = IngestResult(success=True)

        try:
            cursor = self._state.cursor
            total_processed = 0

            while True:
                files, next_cursor = await self.fetch_items(cursor=cursor)

                if not files:
                    break

                for file_data in files:
                    file_result = await self._process_file(file_data)
                    result.documents_created += file_result.documents_created
                    result.entities_created += file_result.entities_created
                    result.errors.extend(file_result.errors)
                    total_processed += 1

                if not next_cursor:
                    break

                cursor = next_cursor
                self._state.cursor = cursor

            self._state.last_sync = datetime.now(UTC)
            self._status = ConnectorStatus.IDLE

            result.metadata["files_processed"] = total_processed

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self._status = ConnectorStatus.ERROR

        return result

    async def _process_file(self, file_data: dict) -> IngestResult:
        """Process a single Google Drive file."""
        result = IngestResult(success=True)

        if not self._client or not self._access_token:
            return result

        try:
            file_id = file_data["id"]
            name = file_data["name"]
            mime_type = file_data["mimeType"]

            # Fetch content based on type
            content = await self._fetch_content(file_id, mime_type)

            if not content:
                return result

            # Parse modified time
            modified_time = None
            if "modifiedTime" in file_data:
                try:
                    modified_time = datetime.fromisoformat(
                        file_data["modifiedTime"].replace("Z", "+00:00")
                    )
                except ValueError as e:
                    logger.debug(f"Could not parse modifiedTime: {e}")

            # Store in Umi
            await self._umi.documents.store(
                source=DocumentSource.DOCS,
                title=name,
                content=content,
                content_type="text/plain",
                metadata={
                    "google_id": file_id,
                    "mime_type": mime_type,
                    "modified_time": modified_time.isoformat() if modified_time else None,
                    "shared": file_data.get("shared", False),
                },
            )
            result.documents_created += 1

            # Create entity for docs that look like projects/notes
            if self._looks_like_entity(name, content):
                entity_type = self._determine_entity_type(name)
                if entity_type:
                    await self._umi.entities.create(
                        type=entity_type,
                        name=name.replace(".md", "").replace(".txt", ""),
                        content=content[:5000],  # Limit content
                        metadata={
                            "source": "google",
                            "google_id": file_id,
                        },
                    )
                    result.entities_created += 1

        except Exception as e:
            result.errors.append(f"Error processing {file_data.get('name', 'unknown')}: {e}")

        return result

    async def _fetch_content(self, file_id: str, mime_type: str) -> str | None:
        """Fetch file content from Google Drive."""
        if not self._client or not self._access_token:
            return None

        try:
            if mime_type == "application/vnd.google-apps.document":
                # Export Google Doc as plain text
                response = await self._client.get(
                    f"{self.DRIVE_API}/files/{file_id}/export",
                    params={"mimeType": "text/plain"},
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
            elif mime_type == "application/vnd.google-apps.spreadsheet":
                # Export as CSV
                response = await self._client.get(
                    f"{self.DRIVE_API}/files/{file_id}/export",
                    params={"mimeType": "text/csv"},
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
            else:
                # Download directly
                response = await self._client.get(
                    f"{self.DRIVE_API}/files/{file_id}",
                    params={"alt": "media"},
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )

            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to fetch content for file {file_id}: HTTP {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to fetch content for file {file_id}: {e}")

        return None

    def _looks_like_entity(self, name: str, content: str) -> bool:
        """Check if a document looks like it should be an entity."""
        name_lower = name.lower()

        # Check filename patterns
        entity_patterns = [
            "project", "plan", "spec", "design",
            "notes", "ideas", "todo", "roadmap",
        ]

        if any(pattern in name_lower for pattern in entity_patterns):
            return True

        # Check if it has structured content (headings, etc)
        if content.startswith("#") or "## " in content:
            return True

        return False

    def _determine_entity_type(self, name: str) -> EntityType | None:
        """Determine entity type from filename."""
        name_lower = name.lower()

        if any(kw in name_lower for kw in ["project", "spec", "design", "roadmap"]):
            return EntityType.PROJECT
        elif any(kw in name_lower for kw in ["note", "idea", "thought"]):
            return EntityType.NOTE
        elif any(kw in name_lower for kw in ["todo", "task", "plan"]):
            return EntityType.TASK
        elif any(kw in name_lower for kw in ["topic", "research", "study"]):
            return EntityType.TOPIC

        return EntityType.NOTE

    async def teardown(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._status = ConnectorStatus.IDLE


async def start_oauth_flow(config: GoogleConnectorConfig) -> str | None:
    """
    Start the OAuth2 flow for Google authentication.

    Returns the authorization URL for the user to visit.
    """
    credentials_path = Path(config.credentials_path).expanduser()

    if not credentials_path.exists():
        return None

    try:
        with open(credentials_path) as f:
            creds = json.load(f)

        client_id = creds.get("installed", {}).get("client_id")
        redirect_uri = creds.get("installed", {}).get("redirect_uris", [""])[0]

        if not client_id:
            return None

        scopes = [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
        ]

        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={' '.join(scopes)}"
            "&access_type=offline"
            "&prompt=consent"
        )

        return auth_url

    except Exception as e:
        logger.warning(f"Failed to start OAuth flow: {e}")
        return None


async def complete_oauth_flow(
    config: GoogleConnectorConfig,
    auth_code: str,
) -> bool:
    """
    Complete the OAuth2 flow with the authorization code.

    Saves the token to the configured token path.
    """
    credentials_path = Path(config.credentials_path).expanduser()
    token_path = Path(config.token_path).expanduser()

    if not credentials_path.exists():
        return False

    try:
        with open(credentials_path) as f:
            creds = json.load(f)

        client_id = creds.get("installed", {}).get("client_id")
        client_secret = creds.get("installed", {}).get("client_secret")
        redirect_uri = creds.get("installed", {}).get("redirect_uris", [""])[0]

        if not all([client_id, client_secret]):
            return False

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": auth_code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if response.status_code != 200:
                return False

            token_data = response.json()

            # Add expiry time
            if "expires_in" in token_data:
                expiry = datetime.now(UTC) + timedelta(seconds=token_data["expires_in"])
                token_data["expiry"] = expiry.isoformat() + "Z"

            # Ensure directory exists
            token_path.parent.mkdir(parents=True, exist_ok=True)

            with open(token_path, "w") as f:
                json.dump(token_data, f)

            return True

    except Exception as e:
        logger.warning(f"Failed to complete OAuth flow: {e}")
        return False
