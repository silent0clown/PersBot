---
name: git_commit
description: Automatically commit changes to Git with meaningful commit messages
version: 1.0.0
author: PersBot
keywords:
  - git
  - commit
  - github
  - version control
commands:
  commit:
    description: Commit all relevant changes with auto-generated message
    usage: persbot skill git_commit commit
    params: {}
  commit-and-push:
    description: Commit and push changes to remote
    usage: persbot skill git_commit commit-and-push
    params:
      remote:
        type: string
        default: origin
        description: Remote name to push to
        branch:
        type: string
        default: main
        description: Branch name to push to
exclude_patterns:
  - dist
  - dist-electron
  - build
  - out
  - __pycache__
  - .pytest_cache
  - node_modules
  - venv
  - env
  - .venv
  - .mypy_cache
  - .ruff_cache
  - .vscode
  - .idea
  - .vs
  - .sublime-project
  - .sublime-workspace
  - "*.log"
  - "*.tmp"
  - "*.temp"
  - logs
  - tmp
  - temp
  - .DS_Store
  - Thumbs.db
  - desktop.ini
  - .env
  - .env.local
  - secrets.json
  - credentials.json
  - .git
  - package-lock.json
  - yarn.lock
  - pnpm-lock.yaml
  - Cargo.lock
dependencies: []
---

# Git Commit Skill

Automatically commits changes to Git with meaningful commit messages based on file types.

## Commands

- `commit` - Commit all relevant changes with auto-generated message
- `commit-and-push` - Commit and push changes to remote

## How It Works

1. Scans git status for modified, untracked, and deleted files
2. Filters out build artifacts, IDE files, and sensitive data
3. Categorizes changes (frontend, backend, config, docs)
4. Generates a conventional commit message
5. Stages and commits the changes

## Requirements

- Git installed
- Valid git repository

## Examples

```bash
persbot skill git_commit commit
persbot skill git_commit commit-and-push remote=origin branch=main
```