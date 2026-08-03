"""Prepare Obsidian Wiki Markdown files for retrieval."""

from __future__ import annotations

import json
from pathlib import Path

from .chunk import chunk_text

WIKI_TYPE_BY_DIR = {
    "components": "component",
    "procedures": "procedure",
    "logs": "log",
    "templates": "template",
}


def iter_wiki_markdown(wiki_dir: Path) -> list[Path]:
    if not wiki_dir.exists():
        raise FileNotFoundError(f"Wiki directory not found: {wiki_dir}")

    paths = []
    for path in wiki_dir.rglob("*.md"):
        if ".obsidian" in path.parts:
            continue
        if "templates" in path.parts:
            continue
        if path.name.lower() == "readme.md":
            continue
        paths.append(path)
    return sorted(paths)


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def wiki_type_for(path: Path, wiki_dir: Path) -> str:
    try:
        relative = path.relative_to(wiki_dir)
    except ValueError:
        return "wiki"
    if not relative.parts:
        return "wiki"
    return WIKI_TYPE_BY_DIR.get(relative.parts[0], "wiki")


def build_wiki_chunks(
    wiki_dir: Path,
    output_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    markdown_paths = iter_wiki_markdown(wiki_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for path in markdown_paths:
            text = path.read_text(encoding="utf-8")
            title = extract_title(text, path.stem)
            relative_source = path.relative_to(wiki_dir.parent).as_posix()
            wiki_type = wiki_type_for(path, wiki_dir)

            for chunk_index, chunk in enumerate(chunk_text(text, chunk_size, chunk_overlap)):
                record = {
                    "source": relative_source,
                    "title": title,
                    "wiki_type": wiki_type,
                    "chunk_id": f"{path.stem}-c{chunk_index}",
                    "text": chunk,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    return count
