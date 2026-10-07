#!/usr/bin/env python3
"""
scripts/clean.py
================
Safe repository cleanup script for Business Automation Workflow DSL Compiler.

Removes ONLY generated and temporary artifacts:
  - Root compiler outputs (*.lst, *.asm, *.dot)
  - output/ directory
  - build/ and dist/ directories
  - __pycache__ directories and *.pyc/*.pyo files
  - Test/coverage caches (.pytest_cache, .coverage, htmlcov)
  - Temporary files (*.tmp, *.log)

NEVER touches:
  - src/
  - tests/
  - examples/
  - docs/
  - web_demo/
  - README.md / report.md
  - requirements.txt / configuration files
"""

import os
import shutil
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Specific protected directories that must NEVER be deleted
PROTECTED_DIRS = {
    ROOT / 'src',
    ROOT / 'tests',
    ROOT / 'examples',
    ROOT / 'docs',
    ROOT / 'web_demo',
    ROOT / 'benchmarks',
    ROOT / 'scripts',
    ROOT / 'data',
}

# Protected files that must NEVER be deleted
PROTECTED_FILES = {
    'README.md',
    'report.md',
    'requirements.txt',
    'requirements-agent.txt',
    '.gitignore',
    '.env.example',
    'Dockerfile',
    'cloudbuild.yaml',
    'cloudrun-service.yaml',
    'server.py',
}


def clean_repository(verbose: bool = True) -> int:
    removed_count = 0
    if verbose:
        print("=" * 65)
        print("  Cleaning generated compiler artifacts and temporary files...")
        print("=" * 65)

    # 1. Root-level generated compiler outputs (*.lst, *.asm, *.dot)
    for ext in ('*.lst', '*.asm', '*.dot', '*.tmp', '*.log'):
        for fpath in ROOT.glob(ext):
            if fpath.is_file() and fpath.name not in PROTECTED_FILES:
                try:
                    fpath.unlink()
                    removed_count += 1
                    if verbose:
                        print(f"  [REMOVED FILE] {fpath.name}")
                except Exception as exc:
                    print(f"  [ERROR] Could not delete {fpath.name}: {exc}")

    # 2. Dedicated generated directories
    for dir_name in ('output', 'build', 'dist', '.pytest_cache', 'htmlcov', '.mypy_cache'):
        target = ROOT / dir_name
        if target.exists() and target.is_dir() and target not in PROTECTED_DIRS:
            try:
                shutil.rmtree(target)
                removed_count += 1
                if verbose:
                    print(f"  [REMOVED DIR]  {dir_name}/")
            except Exception as exc:
                print(f"  [ERROR] Could not delete {dir_name}/: {exc}")

    # 3. Python cache directories (__pycache__) and bytecode (*.pyc)
    # Exclude virtual environments from cleaning
    for pycache in ROOT.rglob('__pycache__'):
        # Skip virtualenvs
        if '.venv' in pycache.parts or 'venv' in pycache.parts or 'env' in pycache.parts:
            continue
        if pycache.is_dir():
            try:
                shutil.rmtree(pycache)
                removed_count += 1
                if verbose:
                    rel_path = pycache.relative_to(ROOT)
                    print(f"  [REMOVED DIR]  {rel_path}/")
            except Exception as exc:
                print(f"  [ERROR] Could not delete {pycache}: {exc}")

    for pyc in ROOT.rglob('*.py[cod]'):
        if '.venv' in pyc.parts or 'venv' in pyc.parts or 'env' in pyc.parts:
            continue
        if pyc.is_file():
            try:
                pyc.unlink()
                removed_count += 1
            except Exception:
                pass

    if verbose:
        print("=" * 65)
        print(f"  ✓ Cleanup completed. Total items removed: {removed_count}")
        print("=" * 65)

    return removed_count


if __name__ == '__main__':
    clean_repository(verbose=True)
