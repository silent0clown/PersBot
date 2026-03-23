#!/usr/bin/env python3
"""
Git Commit Skill for PersBot
This skill automatically commits changes to GitHub with meaningful commit messages.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Set

# Files and directories to exclude from auto-commit
EXCLUDE_PATTERNS = {
    # Build artifacts
    "dist", "dist-electron", "build", "out", "__pycache__", ".pytest_cache",
    "node_modules", "venv", "env", ".venv", ".mypy_cache", ".ruff_cache",
    
    # IDE and editor files  
    ".vscode", ".idea", ".vs", ".sublime-project", ".sublime-workspace",
    
    # Log and temporary files
    "*.log", "*.tmp", "*.temp", "logs", "tmp", "temp",
    
    # System files
    ".DS_Store", "Thumbs.db", "desktop.ini",
    
    # Environment and secrets
    ".env", ".env.local", ".env.*", "secrets.json", "credentials.json",
    
    # Git and version control
    ".git", ".gitignore", ".gitattributes",
    
    # Package manager files
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock",
    
    # Documentation that might be auto-generated
    "docs/_build", "site", ".docusaurus",
}

def should_exclude_file(file_path: str, base_path: str) -> bool:
    """Check if a file should be excluded from auto-commit."""
    from fnmatch import fnmatch
    
    rel_path = os.path.relpath(file_path, base_path)
    rel_path_posix = rel_path.replace(os.sep, '/')
    
    # Check directory patterns
    for pattern in EXCLUDE_PATTERNS:
        if pattern.endswith('/') or '/' in pattern:
            if fnmatch(rel_path_posix, pattern) or fnmatch(rel_path_posix + '/', pattern):
                return True
    
    # Check file patterns
    filename = os.path.basename(rel_path_posix)
    for pattern in EXCLUDE_PATTERNS:
        if not pattern.endswith('/') and '/' not in pattern:
            if fnmatch(filename, pattern) or fnmatch(rel_path_posix, pattern):
                return True
    
    return False

def get_git_status_files() -> dict:
    """Get all files with their git status."""
    try:
        # Get modified and untracked files
        result = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            capture_output=True,
            text=True,
            check=True
        )
        
        modified = []
        untracked = []
        deleted = []
        
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
                
            status = line[:2]
            # Find the first non-whitespace character after status
            filepath_start = 2
            while filepath_start < len(line) and line[filepath_start] == ' ':
                filepath_start += 1
            filepath = line[filepath_start:].strip()
            
            # Handle renamed files
            if '->' in filepath:
                filepath = filepath.split('->')[-1].strip()
            
            if status[1] == 'M':  # Modified
                modified.append(filepath)
            elif status[0] == '?':  # Untracked
                untracked.append(filepath)
            elif status[0] == 'D':  # Deleted
                deleted.append(filepath)
            elif status[0] == 'M':  # Modified in index
                modified.append(filepath)
                
        return {
            'modified': modified,
            'untracked': untracked,
            'deleted': deleted
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Error getting git status: {e}")
        return {'modified': [], 'untracked': [], 'deleted': []}

def generate_commit_message(modified_files: List[str], untracked_files: List[str], deleted_files: List[str]) -> str:
    """Generate a meaningful commit message based on the changes."""
    if not (modified_files or untracked_files or deleted_files):
        return "No changes to commit"
    
    # Categorize changes
    frontend_changes = []
    backend_changes = []
    config_changes = []
    doc_changes = []
    other_changes = []
    
    all_files = modified_files + untracked_files + deleted_files
    
    for filepath in all_files:
        if any(part in filepath.lower() for part in ['frontend', 'electron', 'react', 'src/frontend']):
            frontend_changes.append(filepath)
        elif any(part in filepath.lower() for part in ['backend', 'python', 'src/backend', '.py']):
            backend_changes.append(filepath)
        elif any(part in filepath.lower() for part in ['config', '.json', '.toml', '.yaml', '.yml', '.env']):
            config_changes.append(filepath)
        elif any(part in filepath.lower() for part in ['doc', 'readme', 'spec', '.md']):
            doc_changes.append(filepath)
        else:
            other_changes.append(filepath)
    
    # Generate message
    messages = []
    
    if frontend_changes:
        messages.append("feat: update frontend components and UI")
    if backend_changes:
        messages.append("feat: enhance backend functionality")
    if config_changes:
        messages.append("chore: update configuration files")
    if doc_changes:
        messages.append("docs: update documentation")
    if other_changes and not (frontend_changes or backend_changes or config_changes or doc_changes):
        messages.append("chore: update project files")
    
    if not messages:
        messages.append("chore: update project files")
    
    # Add specific details if there are few changes
    if len(all_files) <= 3:
        specific_files = [os.path.basename(f) for f in all_files[:3]]
        if len(specific_files) == 1:
            messages[0] += f" - {specific_files[0]}"
        elif len(specific_files) <= 3:
            messages[0] += f" - {', '.join(specific_files)}"
    
    return messages[0]

def main():
    """Main function to execute the git commit skill."""
    repo_path = Path.cwd()
    
    # Check if we're in a git repository
    if not (repo_path / ".git").exists():
        print("Error: Not in a git repository")
        sys.exit(1)
    
    # Get git status
    status = get_git_status_files()
    
    if not (status['modified'] or status['untracked'] or status['deleted']):
        print("No changes to commit")
        return
    
    # Filter out excluded files
    base_path = str(repo_path)
    filtered_modified = [f for f in status['modified'] if not should_exclude_file(os.path.join(base_path, f), base_path)]
    filtered_untracked = [f for f in status['untracked'] if not should_exclude_file(os.path.join(base_path, f), base_path)]
    filtered_deleted = [f for f in status['deleted'] if not should_exclude_file(os.path.join(base_path, f), base_path)]
    
    if not (filtered_modified or filtered_untracked or filtered_deleted):
        print("No relevant changes to commit (all changes are in excluded files)")
        return
    
    # Generate commit message
    commit_message = generate_commit_message(filtered_modified, filtered_untracked, filtered_deleted)
    
    # Stage files
    files_to_stage = filtered_modified + filtered_untracked
    if files_to_stage:
        try:
            subprocess.run(["git", "add"] + files_to_stage, check=True)
            print(f"Staged {len(files_to_stage)} files")
        except subprocess.CalledProcessError as e:
            print(f"Error staging files: {e}")
            sys.exit(1)
    
    # Stage deletions
    if filtered_deleted:
        try:
            subprocess.run(["git", "rm", "--cached"] + filtered_deleted, check=True)
            print(f"Staged {len(filtered_deleted)} deletions")
        except subprocess.CalledProcessError as e:
            print(f"Error staging deletions: {e}")
            # Continue anyway
    
    # Create commit
    try:
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print(f"✅ Successfully committed: {commit_message}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating commit: {e}")
        sys.exit(1)
    
    # Optional: Push to remote
    push = input("Push to remote? (y/N): ").strip().lower()
    if push == 'y':
        try:
            subprocess.run(["git", "push"], check=True)
            print("✅ Successfully pushed to remote")
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to remote: {e}")

if __name__ == "__main__":
    main()