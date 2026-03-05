#!/usr/bin/env python3
"""
CLI wrapper for the Git Commit skill
"""

import sys
import os
from pathlib import Path

def main():
    # Add the current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    # Import the main skill
    from git_commit import main as commit_main
    
    # Check if we should auto-push
    if len(sys.argv) > 1 and sys.argv[1] == "--push":
        # Temporarily modify the input to auto-answer 'y' for push
        original_input = input
        def mock_input(prompt):
            if "Push to remote" in prompt:
                return "y"
            return original_input(prompt)
        __builtins__['input'] = mock_input
        
        commit_main()
        __builtins__['input'] = original_input
    else:
        commit_main()

if __name__ == "__main__":
    main()