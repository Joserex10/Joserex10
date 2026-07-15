"""Generate a dated, first-party SVG snapshot from allowlisted public GitHub data."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ALLOWLIST = ("Joserex10/arca-app", "Joserex10/DocuFlow")
API_ROOT = "https://api.github.com"
EXPECTED_WEB_ORIGIN = ("https", "github.com")
USER_AGENT = "Joserex10-profile-snapshot/1.0"
TEMPLATE_VERSION = "2"
MAX_NAME = 100
MAX_TAG = 100
MAX_URL = 500
MAX_SVG_BYTES = 100_000

FORBIDDEN_SVG = re.compile(
    r"<\s*script|foreignobject|\bon[a-z]+\s*=|\bhref\s*=|\bxlink:href\s*=|url\s*\(|data\s*:",
    re.IGNORECASE,
)
FINGERPRINT_PATTERN = re.compile(r'data-fingerprint="([0-9a-f]{64})"')


@dataclass(frozen=True)
class RepositorySignal:
    name: str
    url: str
    pushed_at: datetime


@dataclass(frozen=True)
class ReleaseSignal:
    repository: str
    tag: str
    url: str
    published_at: datetime


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(UTC)


def bounded(value: Any, limit: int, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if len(value) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return value


def github_url(value: Any, field: str) -> str:
    url = bounded(value, MAX_URL, field)
    parsed = urlparse(url)
    if (parsed.scheme, parsed.hostname) != EXPECTED_WEB_ORIGIN:
        raise ValueError(f"{field} must use https://github.com/")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError(f"{field} contains unsupported authority data")
    return url


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": USER_AGENT,
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def get_json(self, path: str) -> Any:
        request = urllib.request.Request(f"{API_ROOT}{path}", headers=self.headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(f"GitHub API returned HTTP {response.status}")
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"GitHub API request failed for {path}") from exc


def fetch_payload(client: GitHubClient) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for full_name in ALLOWLIST:
        payload[full_name] = {
            "repository": client.get_json(f"/repos/{full_name}"),
            "releases": client.get_json(f"/repos/{full_name}/releases?per_page=10"),
        }
    return payload


def normalize(payload: dict[str, dict[str, Any]]) -> tuple[list[RepositorySignal], list[ReleaseSignal]]:
    repositories: list[RepositorySignal] = []
    releases: list[ReleaseSignal] = []

    if set(payload) != set(ALLOWLIST):
        raise ValueError("Payload repositories do not match the fixed allowlist")

    for full_name in ALLOWLIST:
        item = payload[full_name]
        repository = item["repository"]
        expected_name = full_name.split("/", 1)[1]
        name = bounded(repository.get("name"), MAX_NAME, "repository name")
        if name != expected_name:
            raise ValueError(f"Unexpected repository name for {full_name}")

        repositories.append(
            RepositorySignal(
                name=name,
                url=github_url(repository.get("html_url"), "repository URL"),
                pushed_at=parse_timestamp(repository.get("pushed_at")),
            )
        )

        raw_releases = item.get("releases")
        if not isinstance(raw_releases, list):
            raise ValueError("releases must be a list")
        for release in raw_releases:
            if release.get("draft") or release.get("prerelease"):
                continue
            published_at = release.get("published_at")
            if not published_at:
                continue
            releases.append(
                ReleaseSignal(
                    repository=name,
                    tag=bounded(release.get("tag_name"), MAX_TAG, "release tag"),
                    url=github_url(release.get("html_url"), "release URL"),
                    published_at=parse_timestamp(published_at),
                )
            )

    return repositories, releases


def safe_text(value: str) -> str:
    return html.escape(value, quote=True)


def render_svg(payload: dict[str, dict[str, Any]], now: datetime) -> str:
    now = now.astimezone(UTC)
    repositories, releases = normalize(payload)
    latest_repository = max(repositories, key=lambda item: item.pushed_at)
    latest_release = max(releases, key=lambda item: item.published_at, default=None)

    today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
    window_start = today_start - timedelta(days=30)
    recent_pushes = [item for item in repositories if window_start <= item.pushed_at < today_start]
    recent_releases = [item for item in releases if window_start <= item.published_at < today_start]
    signal_count = len(recent_pushes) + len(recent_releases)
    if signal_count:
        activity = f"{signal_count} public shipping signal{'s' if signal_count != 1 else ''} in the last 30 complete UTC days"
        activity_primary = f"{signal_count} public shipping signal{'s' if signal_count != 1 else ''}"
    else:
        activity = "No public shipping activity in the last 30 complete UTC days"
        activity_primary = "No public shipping activity"

    latest_release_text = (
        f"{latest_release.repository} {latest_release.tag} · {latest_release.published_at.date().isoformat()}"
        if latest_release
        else "No stable public release found"
    )
    generated = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data_through = (today_start - timedelta(microseconds=1)).date().isoformat()

    values = {
        "activity": safe_text(activity),
        "activity_primary": safe_text(activity_primary),
        "activity_secondary": "in the last 30 complete UTC days",
        "project": safe_text(f"{latest_repository.name} · pushed {latest_repository.pushed_at.date().isoformat()}"),
        "release": safe_text(latest_release_text),
        "generated": safe_text(generated),
        "through": safe_text(data_through),
    }
    fingerprint_source = "\n".join((TEMPLATE_VERSION, activity, values["project"], values["release"]))
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="300" viewBox="0 0 1200 300" role="img" aria-labelledby="title description" data-template-version="{TEMPLATE_VERSION}" data-fingerprint="{fingerprint}">
  <title id="title">Public shipping snapshot</title>
  <desc id="description">Dated historical snapshot for Arca and DocuFlow. {values["activity"]}.</desc>
  <style>
    .bg{{fill:#F7F7F4}}.panel{{fill:#FFFFFF;stroke:#D0D7DE}}.ink{{fill:#161B22}}.muted{{fill:#57606A}}.rule{{stroke:#D0D7DE}}.accent{{fill:#0969DA}}.sans{{font-family:Inter,Segoe UI,Arial,sans-serif}}.mono{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}
    @media (prefers-color-scheme:dark){{.bg{{fill:#0D1117}}.panel{{fill:#161B22;stroke:#30363D}}.ink{{fill:#F0F6FC}}.muted{{fill:#8C959F}}.rule{{stroke:#30363D}}.accent{{fill:#58A6FF}}}}
  </style>
  <rect class="bg" width="1200" height="300" rx="18"/>
  <rect class="panel" x="28" y="28" width="1144" height="244" rx="12"/>
  <text class="mono accent" x="60" y="66" font-size="13" letter-spacing="2">PUBLIC SHIPPING / HISTORICAL SNAPSHOT</text>
  <text class="mono muted" x="1140" y="66" text-anchor="end" font-size="12">DATA THROUGH {values["through"]} UTC</text>
  <line class="rule" x1="60" y1="88" x2="1140" y2="88"/>
  <text class="mono muted" x="60" y="122" font-size="12" letter-spacing="1.4">30-DAY WINDOW</text>
  <text class="sans ink" x="60" y="154" font-size="21" font-weight="600">{values["activity_primary"]}</text>
  <text class="sans muted" x="60" y="181" font-size="16">{values["activity_secondary"]}</text>
  <text class="mono muted" x="60" y="218" font-size="12" letter-spacing="1.4">LATEST SELECTED PROJECT</text>
  <text class="sans ink" x="60" y="248" font-size="18">{values["project"]}</text>
  <line class="rule" x1="620" y1="112" x2="620" y2="254"/>
  <text class="mono muted" x="660" y="122" font-size="12" letter-spacing="1.4">LATEST STABLE RELEASE</text>
  <text class="sans ink" x="660" y="158" font-size="21" font-weight="600">{values["release"]}</text>
  <text class="mono muted" x="660" y="218" font-size="12" letter-spacing="1.4">GENERATED</text>
  <text class="sans ink" x="660" y="248" font-size="18">{values["generated"]}</text>
</svg>'''


def validate_svg(svg: str) -> None:
    encoded = svg.encode("utf-8")
    if len(encoded) > MAX_SVG_BYTES:
        raise ValueError(f"SVG exceeds {MAX_SVG_BYTES} bytes")
    if FORBIDDEN_SVG.search(svg):
        raise ValueError("SVG contains a forbidden construct")
    ET.fromstring(svg)


def fingerprint(svg: str) -> str:
    match = FINGERPRINT_PATTERN.search(svg)
    if not match:
        raise ValueError("SVG is missing its data fingerprint")
    return match.group(1)


def atomic_write(output: Path, svg: str) -> bool:
    validate_svg(svg)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        current = output.read_text(encoding="utf-8")
        try:
            if fingerprint(current) == fingerprint(svg):
                return False
        except ValueError:
            pass
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=output.parent, delete=False) as handle:
            handle.write(svg)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, output)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    return True


def load_fixture(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("assets/activity.svg"))
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--now", help="ISO-8601 timestamp used for deterministic tests")
    args = parser.parse_args()

    now = parse_timestamp(args.now) if args.now else datetime.now(UTC)
    payload = load_fixture(args.fixture) if args.fixture else fetch_payload(GitHubClient(os.getenv("GITHUB_TOKEN")))
    atomic_write(args.output, render_svg(payload, now))


if __name__ == "__main__":
    main()
