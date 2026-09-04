"""Immutable source snapshots with hash-based drift detection.

Snapshots live in knowledge/hong_kong/fsie/raw/ (git-ignored). A snapshot is
written once and never overwritten; if the upstream content changes, a new
snapshot appears and the hash mismatch is surfaced, never absorbed silently.
"""

from __future__ import annotations

import hashlib
import io
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from packages.knowledge_loader import parser as knowledge_parser

RAW_DIR = knowledge_parser.FSIE_DIR / "raw"
USER_AGENT = "asia-tax-agent-l0-research/0.1 (synthetic-data research prototype)"


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    content: bytes
    sha256: str
    snapshot_path: Path
    http_status: int
    reused: bool
    drift: bool  # True when the live content no longer matches the manifest hash


def _check_domain(url: str, allowed: list[str]) -> None:
    host = urlparse(url).netloc.lower()
    if host not in {d.lower() for d in allowed}:
        raise FetchError(f"host {host!r} is not in the manifest allowlist")


def _download(url: str, timeout: float = 300.0) -> tuple[bytes, int]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            buffer = io.BytesIO()
            while chunk := resp.read(1 << 16):
                buffer.write(chunk)
            return buffer.getvalue(), resp.status
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"transport error for {url}: {exc.reason}") from exc


def _existing_snapshot(source_dir: Path) -> Path | None:
    """Reuse the newest snapshot in place. Drifted sources keep their new-hash
    snapshot; forcing a fresh download requires deleting the raw directory."""
    if not source_dir.exists():
        return None
    files = [c for c in sorted(source_dir.iterdir()) if c.is_file()]
    return files[-1] if files else None


def fetch_source(entry: dict, allowed_domains: list[str], *, timeout: float = 300.0) -> FetchResult:
    source_id = entry["source_id"]
    manifest_sha = entry.get("content_sha256")
    source_dir = RAW_DIR / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    existing = _existing_snapshot(source_dir)
    if existing is not None:
        content = existing.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        return FetchResult(
            source_id=source_id, content=content, sha256=sha,
            snapshot_path=existing, http_status=200, reused=True,
            drift=bool(manifest_sha and sha != manifest_sha),
        )

    structured_url = entry.get("structured_data_url")
    url = structured_url or entry["url"]
    _check_domain(url, allowed_domains)
    raw_bytes, status = _download(url, timeout=timeout)

    if structured_url and entry.get("structured_file"):
        # Transport bundle (zip): extract the registered member.
        member = entry["structured_file"].replace("/", "\\")
        archive = zipfile.ZipFile(io.BytesIO(raw_bytes))
        names = {n.replace("\\", "/"): n for n in archive.namelist()}
        wanted = entry["structured_file"]
        if wanted not in names:
            raise FetchError(f"structured_file {wanted!r} missing from bundle")
        content = archive.read(names[wanted])
        extension = Path(wanted).suffix
    else:
        content = raw_bytes
        extension = ".pdf" if b"%PDF" in content[:8] else (
            ".xml" if content.lstrip()[:5] == b"<?xml" else ".html"
        )

    sha = hashlib.sha256(content).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot = source_dir / f"{stamp}-{sha[:16]}{extension}"
    snapshot.write_bytes(content)
    return FetchResult(
        source_id=source_id, content=content, sha256=sha, snapshot_path=snapshot,
        http_status=status, reused=False,
        drift=bool(manifest_sha and sha != manifest_sha),
    )


def manifest() -> dict:
    return knowledge_parser._read_json(knowledge_parser.FSIE_DIR / "source_manifest.json")
