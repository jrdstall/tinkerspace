"""Deployment and installation script for Tinkerspace (Innovator's Workspace).

Deploys a clean, standalone production instance into a separate directory
(default: C:\\Users\\jrdst\\software\\IW) without development tests or design docs.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy Tinkerspace to a standalone directory.")
    parser.add_argument(
        "--target",
        type=str,
        default=r"C:\Users\jrdst\software\IW",
        help="Target installation directory",
    )
    parser.add_argument(
        "--vault-repo",
        type=str,
        default="",
        help="Git repository URL for private personal vault (optional)",
    )
    return parser.parse_args()


def create_target_environment(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    venv_dir = target_dir / ".venv"
    if not venv_dir.exists():
        print(f"Creating Python virtual environment in {venv_dir}...")
        subprocess.run(["uv", "venv", str(venv_dir)], check=True)
    return venv_dir


def install_package(target_dir: Path, source_dir: Path) -> None:
    venv_python = target_dir / ".venv" / "Scripts" / "python.exe"
    print("Installing Tinkerspace application package into standalone environment...")
    subprocess.run(
        ["uv", "pip", "install", "-e", str(source_dir), "--python", str(venv_python)],
        check=True,
    )


def copy_static_assets(source_dir: Path, target_dir: Path) -> None:
    print("Copying activity templates and documentation...")
    src_templates = source_dir / "content" / "templates"
    dest_templates = target_dir / "content" / "templates"
    dest_templates.parent.mkdir(parents=True, exist_ok=True)
    if src_templates.exists():
        if dest_templates.exists():
            shutil.rmtree(dest_templates)
        shutil.copytree(src_templates, dest_templates)

    user_guide_src = source_dir / "docs" / "USER_GUIDE.md"
    if user_guide_src.exists():
        shutil.copy2(user_guide_src, target_dir / "USER_GUIDE.md")


def setup_vault_directory(target_dir: Path, vault_repo: str) -> None:
    vault_dir = target_dir / "vault"
    if vault_dir.exists() and (vault_dir / ".git").exists():
        print(f"Vault already exists at {vault_dir}; keeping existing data untouched.")
        return

    if vault_repo:
        print(f"Cloning vault repository from {vault_repo}...")
        subprocess.run(["git", "clone", vault_repo, str(vault_dir)], check=True)
    else:
        print(f"Initializing clean local datastore in {vault_dir}...")
        vault_dir.mkdir(parents=True, exist_ok=True)
        for sub in ["notes", "work", "inbox/drop", "cas", "meta"]:
            (vault_dir / sub).mkdir(parents=True, exist_ok=True)
        (vault_dir / "events.jsonl").touch(exist_ok=True)
        (vault_dir / "inbox" / "raw.jsonl").touch(exist_ok=True)
        try:
            subprocess.run(["git", "init", str(vault_dir)], check=True, capture_output=True)
        except Exception:
            pass


def generate_launchers(target_dir: Path) -> None:
    print("Generating Windows double-clickable launchers...")
    bat_content = (
        "@echo off\r\n"
        "title Tinkerspace (Innovator's Workspace)\r\n"
        'cd /d "%~dp0"\r\n'
        'set "IW_VAULT_DIR=%~dp0vault"\r\n'
        "echo ====================================================\r\n"
        "echo   Tinkerspace Production Instance\r\n"
        "echo   Vault: %IW_VAULT_DIR%\r\n"
        "echo   URL:   http://localhost:8000\r\n"
        "echo ====================================================\r\n"
        'start "" http://localhost:8000\r\n'
        '".venv\\Scripts\\uvicorn.exe" iw.web.app:app --port 8000 --reload\r\n'
        "pause\r\n"
    )
    with open(target_dir / "start.bat", "w", encoding="utf-8") as f:
        f.write(bat_content)

    ps1_content = (
        "$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path\r\n"
        "Set-Location $scriptDir\r\n"
        '$env:IW_VAULT_DIR = Join-Path $scriptDir "vault"\r\n'
        'Write-Host "====================================================" -ForegroundColor Cyan\r\n'
        'Write-Host "  Tinkerspace Production Instance" -ForegroundColor Cyan\r\n'
        'Write-Host "  Vault: $env:IW_VAULT_DIR" -ForegroundColor DarkGray\r\n'
        'Write-Host "  URL:   http://localhost:8000" -ForegroundColor Green\r\n'
        'Write-Host "====================================================" -ForegroundColor Cyan\r\n'
        'Start-Process "http://localhost:8000"\r\n'
        '& "$scriptDir\\.venv\\Scripts\\uvicorn.exe" iw.web.app:app --port 8000 --reload\r\n'
    )
    with open(target_dir / "start.ps1", "w", encoding="utf-8") as f:
        f.write(ps1_content)


def main() -> None:
    args = parse_args()
    target_dir = Path(args.target).resolve()
    source_dir = Path(__file__).resolve().parent.parent

    print(f"=== Deploying Tinkerspace to {target_dir} ===")
    create_target_environment(target_dir)
    install_package(target_dir, source_dir)
    copy_static_assets(source_dir, target_dir)
    setup_vault_directory(target_dir, args.vault_repo)
    generate_launchers(target_dir)
    print("\n[SUCCESS] Tinkerspace successfully deployed!")
    print(f"To launch: double-click '{target_dir / 'start.bat'}' or run '{target_dir / 'start.ps1'}'")


if __name__ == "__main__":
    main()
