"""
Git Repository Connector

Ingests Git repository metadata into Umi:
- Repository info as project entity
- README content
- Recent commits
- File structure overview
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rikaios.core.models import DocumentSource, EntityType
from rikaios.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorMode,
    ConnectorStatus,
    IngestResult,
)


@dataclass
class GitConnectorConfig(ConnectorConfig):
    """Configuration for the Git connector."""
    repo_paths: list[str] = field(default_factory=list)
    include_commits: bool = True
    commit_limit: int = 50
    include_readme: bool = True
    include_structure: bool = True


@dataclass
class RepoInfo:
    """Information about a Git repository."""
    path: Path
    name: str
    remote_url: str | None = None
    branch: str = "main"
    last_commit: str | None = None
    last_commit_date: datetime | None = None
    commit_count: int = 0


class GitConnector(BaseConnector):
    """
    Connector for Git repositories.

    Extracts repository metadata and stores as project entities.
    """

    name = "git"
    mode = ConnectorMode.PULL
    description = "Git repository connector"

    def __init__(self, config: GitConnectorConfig | None = None) -> None:
        super().__init__(config or GitConnectorConfig())
        self._config: GitConnectorConfig

    async def setup(self) -> None:
        """Verify git is available."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("Git not found")
            self._status = ConnectorStatus.IDLE
        except FileNotFoundError:
            self._status = ConnectorStatus.ERROR
            raise RuntimeError("Git not installed")

    async def sync(self) -> IngestResult:
        """Sync all configured repositories."""
        if not self._umi:
            return IngestResult(success=False, errors=["Not initialized"])

        self._status = ConnectorStatus.RUNNING
        result = IngestResult(success=True)

        try:
            for repo_path in self._config.repo_paths:
                path = Path(repo_path).expanduser()
                if not path.exists():
                    result.errors.append(f"Path not found: {repo_path}")
                    continue

                repo_result = await self._process_repo(path)
                result.documents_created += repo_result.documents_created
                result.entities_created += repo_result.entities_created
                result.errors.extend(repo_result.errors)

            self._state.last_sync = datetime.utcnow()
            self._status = ConnectorStatus.IDLE

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self._status = ConnectorStatus.ERROR

        return result

    async def add_repo(self, path: str) -> IngestResult:
        """Add and sync a single repository."""
        repo_path = Path(path).expanduser()
        if not repo_path.exists():
            return IngestResult(success=False, errors=[f"Path not found: {path}"])

        # Add to config if not already there
        if path not in self._config.repo_paths:
            self._config.repo_paths.append(path)

        return await self._process_repo(repo_path)

    async def _process_repo(self, path: Path) -> IngestResult:
        """Process a single repository."""
        result = IngestResult(success=True)

        try:
            # Get repo info
            info = self._get_repo_info(path)
            if not info:
                result.errors.append(f"Not a git repo: {path}")
                return result

            # Create/update project entity
            content_parts = [
                f"Git repository: {info.name}",
                f"Path: {info.path}",
            ]

            if info.remote_url:
                content_parts.append(f"Remote: {info.remote_url}")
            content_parts.append(f"Branch: {info.branch}")
            if info.last_commit:
                content_parts.append(f"Last commit: {info.last_commit}")
            content_parts.append(f"Total commits: {info.commit_count}")

            # Add README if exists
            if self._config.include_readme:
                readme = self._get_readme(path)
                if readme:
                    content_parts.extend(["", "## README", "", readme])

            # Add structure if configured
            if self._config.include_structure:
                structure = self._get_structure(path)
                if structure:
                    content_parts.extend(["", "## Structure", "", "```", structure, "```"])

            content = "\n".join(content_parts)

            # Create entity
            await self._umi.entities.create(
                type=EntityType.PROJECT,
                name=info.name,
                content=content,
                metadata={
                    "source": "git",
                    "path": str(path),
                    "remote_url": info.remote_url,
                    "branch": info.branch,
                    "commit_count": info.commit_count,
                },
            )
            result.entities_created += 1

            # Store commits as document
            if self._config.include_commits:
                commits = self._get_commits(path, self._config.commit_limit)
                if commits:
                    await self._umi.documents.store(
                        source=DocumentSource.GIT,
                        title=f"{info.name} - Commit History",
                        content=commits,
                        metadata={
                            "repo": info.name,
                            "path": str(path),
                        },
                    )
                    result.documents_created += 1

        except Exception as e:
            result.errors.append(f"Error processing {path}: {e}")

        return result

    def _get_repo_info(self, path: Path) -> RepoInfo | None:
        """Get repository information."""
        try:
            # Check if it's a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return None

            # Get repo name
            name = path.name

            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            remote_url = result.stdout.strip() if result.returncode == 0 else None

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            branch = result.stdout.strip() or "main"

            # Get last commit
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%s|%ai"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            last_commit = None
            last_commit_date = None
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("|")
                if len(parts) >= 2:
                    last_commit = f"{parts[0][:8]}: {parts[1]}"
                if len(parts) >= 3:
                    try:
                        last_commit_date = datetime.fromisoformat(parts[2].strip())
                    except ValueError:
                        pass

            # Get commit count
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            commit_count = int(result.stdout.strip()) if result.returncode == 0 else 0

            return RepoInfo(
                path=path,
                name=name,
                remote_url=remote_url,
                branch=branch,
                last_commit=last_commit,
                last_commit_date=last_commit_date,
                commit_count=commit_count,
            )

        except Exception:
            return None

    def _get_readme(self, path: Path) -> str | None:
        """Get README content."""
        readme_names = ["README.md", "README", "readme.md", "Readme.md"]
        for name in readme_names:
            readme_path = path / name
            if readme_path.exists():
                try:
                    content = readme_path.read_text()
                    # Limit size
                    if len(content) > 5000:
                        content = content[:5000] + "\n\n... (truncated)"
                    return content
                except Exception:
                    pass
        return None

    def _get_structure(self, path: Path, max_depth: int = 3) -> str | None:
        """Get directory structure."""
        try:
            result = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", "HEAD"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return None

            files = result.stdout.strip().split("\n")[:100]  # Limit files

            # Build tree structure
            tree_lines = []
            for file in files:
                depth = file.count("/")
                if depth < max_depth:
                    indent = "  " * depth
                    name = file.split("/")[-1]
                    tree_lines.append(f"{indent}{name}")

            return "\n".join(tree_lines[:50])  # Limit output

        except Exception:
            return None

    def _get_commits(self, path: Path, limit: int) -> str | None:
        """Get recent commit history."""
        try:
            result = subprocess.run(
                ["git", "log", f"-{limit}", "--format=%h|%s|%an|%ar"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return None

            lines = ["# Commit History", ""]
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        lines.append(f"- `{parts[0]}` {parts[1]} ({parts[2]}, {parts[3]})")

            return "\n".join(lines)

        except Exception:
            return None
