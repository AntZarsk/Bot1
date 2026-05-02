from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_fact_key(source: str, source_id: str, text: str) -> str:
    payload = f"{source}:{source_id}:{text.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_used_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def append_used_key(path: Path, key: str) -> None:
    ensure_parent_dir(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{key}\n")


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def safe_json_loads(text: str) -> dict:
    return json.loads(text)


def chunk_list(items: List[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def read_cycle_index(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return 0


def write_cycle_index(path: Path, index: int) -> None:
    ensure_parent_dir(path)
    path.write_text(str(index), encoding="utf-8")
