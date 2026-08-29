"""Local Git commit adapter for vault storage operations.

Layer 3 Adapter. Interacts with the local git binary via subprocess.
"""

from pathlib import Path
import subprocess

from iw.contracts.models import Author, AuthorKind


class GitCommitter:
    """Performs atomic local git commits on store mutations and sync ingestion."""

    def __init__(self, vault_dir: Path) -> None:
        self.vault_dir = vault_dir

    def is_git_repo(self) -> bool:
        """Check whether vault directory is a valid git repository."""
        return (self.vault_dir / ".git").exists()

    def get_uncommitted_files(self) -> list[Path]:
        """Return list of modified or untracked file paths in the vault."""
        if not self.is_git_repo():
            return []
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain", "-uall"],
                cwd=str(self.vault_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                return []
            uncommitted: list[Path] = []
            for line in res.stdout.splitlines():
                if len(line) > 3:
                    rel_path = line[3:].strip().strip('"')
                    full_path = self.vault_dir / rel_path
                    if full_path.is_file():
                        uncommitted.append(full_path)
            return uncommitted
        except (OSError, subprocess.SubprocessError):
            return []


    def commit_file(
        self,
        file_path: Path,
        commit_message: str,
        author: Author,
    ) -> bool:
        """Stage and commit a single modified or created file in the vault."""
        if not self.is_git_repo():
            return False

        try:
            rel_path = file_path.relative_to(self.vault_dir)
        except ValueError:
            rel_path = file_path

        author_str = self._format_git_author(author)
        try:
            add_res = subprocess.run(
                ["git", "add", str(rel_path)],
                cwd=str(self.vault_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if add_res.returncode != 0:
                return False

            commit_res = subprocess.run(
                ["git", "commit", "-m", commit_message, f"--author={author_str}"],
                cwd=str(self.vault_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            return commit_res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def commit_all_uncommitted(
        self,
        author: Author,
        message: str = "sync: commit external notes from sync",
    ) -> list[Path]:
        """Stage and commit all uncommitted files arriving via sync."""
        uncommitted = self.get_uncommitted_files()
        if not uncommitted or not self.is_git_repo():
            return []

        author_str = self._format_git_author(author)
        try:
            subprocess.run(
                ["git", "add", "."],
                cwd=str(self.vault_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            commit_res = subprocess.run(
                ["git", "commit", "-m", message, f"--author={author_str}"],
                cwd=str(self.vault_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            return uncommitted if commit_res.returncode == 0 else []
        except (OSError, subprocess.SubprocessError):
            return []

    def _format_git_author(self, author: Author) -> str:
        """Format Author into standard Git author string 'Name <email>'."""
        if author.kind == AuthorKind.HUMAN:
            return "Jared <jared@innovators.local>"
        if author.kind == AuthorKind.AGENT:
            model_info = author.declared_model or author.requested_model or "agent"
            return f"Tinkerspace Agent ({model_info}) <agent@innovators.local>"
        if author.kind == AuthorKind.TOOL:
            return f"Tinkerspace Tool ({author.courier}) <tool@innovators.local>"
        return "External Sync <sync@innovators.local>"
