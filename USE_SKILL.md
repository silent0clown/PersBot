# Using the Git Commit Skill

## Quick Start

To use the Git Commit skill, run:

```bash
# Commit changes with auto-generated message
python skill/git_commit.py

# Commit and auto-push
python skill/git_commit_cli.py --push
```

## Features

- **Smart filtering**: Automatically excludes build artifacts, logs, secrets, and temporary files
- **Contextual messages**: Generates appropriate commit messages based on file types changed
- **Safe operation**: Never commits sensitive files like `.env` or credentials
- **Easy integration**: Works with any Git repository

## Excluded Files

The skill automatically excludes:
- Build directories: `dist/`, `build/`, `node_modules/`
- IDE files: `.vscode/`, `.idea/`
- Log files: `*.log`, `logs/`
- Secrets: `.env`, `credentials.json`
- System files: `.DS_Store`, `Thumbs.db`
- Package locks: `package-lock.json`, `yarn.lock`

## Customization

Edit `skill/git_commit.py` to modify the `EXCLUDE_PATTERNS` set for custom exclusions.

## Integration with PersBot

This skill can be integrated into PersBot's voice command system to enable commands like:
- "Commit my changes"
- "Save to GitHub"
- "Push my work"