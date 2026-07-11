#!/usr/bin/env python3
"""
Intelligent Git Conflict Resolver
==================================
Auto-resolves merge conflicts following AGENTS.md strategies.
Handles blog posts, images, and configuration files intelligently.

Usage:
  python3 scripts/conflict-resolver.py --auto-resolve    # Auto-resolve conflicts
  python3 scripts/conflict-resolver.py --status           # Show conflict status
  python3 scripts/conflict-resolver.py --preview          # Preview resolution
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

class ConflictResolver:
    """Intelligent merge conflict resolver."""

    def __init__(self):
        self.repo_root = REPO_ROOT
        self.conflicts = []

    def detect_conflicts(self) -> List[str]:
        """Detect files with merge conflicts."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', '--diff-filter=U'],
                capture_output=True, text=True, cwd=str(self.repo_root)
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except Exception as e:
            print(f"❌ Error detecting conflicts: {e}")
            return []

    def get_file_content(self, filepath: str, version: str) -> str:
        """Get file content from specific version (ours/theirs)."""
        try:
            result = subprocess.run(
                ['git', 'show', f':{version}:{filepath}'],
                capture_output=True, text=True, cwd=str(self.repo_root)
            )
            return result.stdout
        except Exception:
            return ""

    def should_take_theirs(self, filepath: str) -> bool:
        """Decide whether to take theirs version based on path."""
        theirs_paths = [
            'content/posts/',  # Blog posts
            'data/images.json',  # Image metadata
            'data/image-selection-report.json',  # Image reports
            'static/images/posts/',  # Post images
        ]
        return any(filepath.startswith(p) for p in theirs_paths)

    def should_take_ours(self, filepath: str) -> bool:
        """Decide whether to take ours version based on path."""
        ours_paths = [
            '.github/workflows/',  # CI/CD workflows
            'AGENTS.md',  # Main rules
            'config/',  # Configuration
        ]
        return any(filepath.startswith(p) for p in ours_paths)

    def resolve_conflict_intelligent(self, filepath: str) -> Tuple[bool, str]:
        """Resolve a single conflict intelligently."""
        try:
            if self.should_take_theirs(filepath):
                subprocess.run(
                    ['git', 'checkout', '--theirs', filepath],
                    cwd=str(self.repo_root), check=True
                )
                return True, f"✓ {filepath}: Took incoming (theirs) version"

            elif self.should_take_ours(filepath):
                subprocess.run(
                    ['git', 'checkout', '--ours', filepath],
                    cwd=str(self.repo_root), check=True
                )
                return True, f"✓ {filepath}: Kept current (ours) version"

            else:
                # Try to merge TOML files intelligently
                if filepath.endswith('.md') or filepath.endswith('.json'):
                    ours = self.get_file_content(filepath, '1')
                    theirs = self.get_file_content(filepath, '3')

                    if filepath.startswith('content/posts/'):
                        # For blog posts, prefer theirs (incoming changes)
                        subprocess.run(
                            ['git', 'checkout', '--theirs', filepath],
                            cwd=str(self.repo_root), check=True
                        )
                        return True, f"✓ {filepath}: Blog post resolved (theirs)"
                    else:
                        # For others, prefer ours
                        subprocess.run(
                            ['git', 'checkout', '--ours', filepath],
                            cwd=str(self.repo_root), check=True
                        )
                        return True, f"✓ {filepath}: File resolved (ours)"

            return False, f"⚠ {filepath}: Could not auto-resolve"

        except Exception as e:
            return False, f"❌ {filepath}: {e}"

    def resolve_all(self) -> Dict:
        """Resolve all conflicts."""
        conflicts = self.detect_conflicts()

        if not conflicts or conflicts == ['']:
            return {'status': 'no_conflicts', 'message': '✅ No conflicts found'}

        results = {
            'total': len(conflicts),
            'resolved': 0,
            'failed': 0,
            'messages': []
        }

        for filepath in conflicts:
            if not filepath:
                continue

            success, message = self.resolve_conflict_intelligent(filepath)
            results['messages'].append(message)

            if success:
                results['resolved'] += 1
            else:
                results['failed'] += 1

        # Add all resolved files to staging
        if results['resolved'] > 0:
            try:
                subprocess.run(
                    ['git', 'add', '-A'],
                    cwd=str(self.repo_root), check=True
                )
                results['messages'].append("✓ All resolved files staged for commit")
            except Exception as e:
                results['messages'].append(f"⚠ Failed to stage files: {e}")

        return results

    def show_status(self) -> None:
        """Show current conflict status."""
        conflicts = self.detect_conflicts()

        if not conflicts or conflicts == ['']:
            print("✅ No merge conflicts found")
            return

        print(f"🔴 Found {len(conflicts)} file(s) with conflicts:\n")
        for filepath in conflicts:
            if filepath:
                print(f"  - {filepath}")

    def preview_resolution(self) -> None:
        """Show preview of how conflicts will be resolved."""
        conflicts = self.detect_conflicts()

        if not conflicts or conflicts == ['']:
            print("✅ No conflicts to resolve")
            return

        print("📋 CONFLICT RESOLUTION PREVIEW:\n")
        for filepath in conflicts:
            if filepath:
                if self.should_take_theirs(filepath):
                    print(f"  {filepath}: ➜ Will take THEIRS (incoming)")
                elif self.should_take_ours(filepath):
                    print(f"  {filepath}: ➜ Will take OURS (current)")
                else:
                    print(f"  {filepath}: ➜ Will use intelligent merge")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Git Conflict Resolver')
    parser.add_argument('--auto-resolve', action='store_true', help='Auto-resolve all conflicts')
    parser.add_argument('--status', action='store_true', help='Show conflict status')
    parser.add_argument('--preview', action='store_true', help='Preview resolution')

    args = parser.parse_args()

    resolver = ConflictResolver()

    if args.status or (not args.auto_resolve and not args.preview):
        resolver.show_status()

    if args.preview:
        resolver.preview_resolution()

    if args.auto_resolve:
        print("🔧 Auto-resolving conflicts...\n")
        results = resolver.resolve_all()

        if results.get('status') == 'no_conflicts':
            print(results['message'])
            return 0

        for message in results['messages']:
            print(message)

        print(f"\n📊 Summary:")
        print(f"  Total: {results['total']}")
        print(f"  Resolved: {results['resolved']}")
        print(f"  Failed: {results['failed']}")

        if results['resolved'] == results['total']:
            print("\n✅ All conflicts resolved! Ready to commit.")
            return 0
        else:
            print(f"\n⚠ {results['failed']} conflict(s) need manual resolution")
            return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
