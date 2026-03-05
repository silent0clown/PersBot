# Git Commit Skill for PersBot

This skill automatically commits your changes to GitHub with meaningful commit messages.

## Features

- **Smart file filtering**: Automatically excludes build artifacts, logs, secrets, and other files that shouldn't be committed
- **Contextual commit messages**: Generates appropriate commit messages based on the types of files changed
- **Safe operation**: Only commits files that are safe to commit (no secrets or sensitive files)
- **Easy integration**: Works seamlessly with your existing Git workflow

## Usage

### Basic Usage

```bash
# Navigate to your project root
cd /path/to/your/project

# Run the skill to commit changes
python skill/git_commit.py

# Or use the CLI wrapper
python skill/git_commit_cli.py

# Auto-commit and push
python skill/git_commit_cli.py --push
```

### Integration with PersBot

Once integrated into PersBot, you can use voice commands like:
- "Commit my changes"
- "Save to GitHub"
- "Push my work"

## Excluded Files

The skill automatically excludes the following types of files:

- **Build artifacts**: `dist/`, `build/`, `node_modules/`, `__pycache__/`
- **IDE files**: `.vscode/`, `.idea/`, `.vs/`
- **Log files**: `*.log`, `logs/`
- **Secrets**: `.env`, `secrets.json`, `credentials.json`
- **System files**: `.DS_Store`, `Thumbs.db`
- **Package locks**: `package-lock.json`, `yarn.lock`

## Configuration

You can customize the excluded patterns by modifying the `EXCLUDE_PATTERNS` set in `git_commit.py`.

## Requirements

- Python 3.6+
- Git installed and configured
- The project must be a Git repository

## License

MIT License