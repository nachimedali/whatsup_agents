"""
Repository context loader.

Reads files from a local path using glob patterns and assembles them
into a formatted string block that gets injected into the user message
before it reaches Claude.
"""

import os
import glob as glob_module
from pathlib import Path

# Hard cap to avoid blowing the context window
MAX_REPO_CHARS = int(os.getenv("MAX_REPO_CHARS", str(80_000)))
# Files larger than this are truncated individually
MAX_FILE_CHARS = int(os.getenv("MAX_FILE_CHARS", str(20_000)))

# Extensions we bother reading (skip binaries, images, etc.)
TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".java", ".kt", ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
    ".sql", ".sh", ".bash", ".zsh",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".env.example",
    ".md", ".mdx", ".txt", ".rst",
    ".html", ".css", ".scss", ".svelte", ".vue",
    ".xml", ".graphql", ".proto",
    "Makefile", "Dockerfile", ".dockerignore", ".gitignore",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".mypy_cache",
    ".pytest_cache", ".ruff_cache",
}


def _is_text_file(path: Path) -> bool:
    if path.name in TEXT_EXTENSIONS:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def _collect_files(repo_path: str, globs: list[str]) -> list[Path]:
    """Return a de-duplicated list of readable text files."""
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    seen: set[Path] = set()
    files: list[Path] = []

    patterns = globs if globs else ["**/*"]
    for pattern in patterns:
        for match in root.glob(pattern):
            if not match.is_file():
                continue
            # Skip unwanted dirs
            parts = match.relative_to(root).parts
            if any(p in SKIP_DIRS for p in parts):
                continue
            if not _is_text_file(match):
                continue
            if match not in seen:
                seen.add(match)
                files.append(match)

    files.sort()
    return files


def _read_file(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"=== {rel} ===\n[Could not read: {e}]\n"

    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + f"\n... [truncated at {MAX_FILE_CHARS} chars]"

    return f"=== {rel} ===\n{content}\n"


def load_repository_context(repo_path: str, globs: list[str]) -> str:
    """
    Build the full repo context block to inject into the prompt.
    Returns a formatted string listing all matching files with their contents.
    """
    root = Path(repo_path).resolve()
    files = _collect_files(repo_path, globs)

    if not files:
        return f"[Repository at {repo_path} — no matching files found for globs: {globs or ['**/*']}]"

    blocks: list[str] = []
    total = 0

    for f in files:
        block = _read_file(f, root)
        if total + len(block) > MAX_REPO_CHARS:
            blocks.append(
                f"\n... [Remaining {len(files) - len(blocks)} file(s) omitted — "
                f"hit {MAX_REPO_CHARS:,} char limit]"
            )
            break
        blocks.append(block)
        total += len(block)

    header = (
        f"Repository: {repo_path}\n"
        f"Files loaded: {len(blocks)} / {len(files)}\n"
        f"{'─' * 60}\n\n"
    )
    return header + "\n".join(blocks)


def get_file_tree(repo_path: str, globs: list[str]) -> list[str]:
    """Return a list of relative file paths (for display in the UI)."""
    root = Path(repo_path).resolve()
    try:
        files = _collect_files(repo_path, globs)
        return [str(f.relative_to(root)) for f in files]
    except FileNotFoundError:
        return []
