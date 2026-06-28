#!/usr/bin/env python3
"""Write temporary Apple XCUITest config and journey files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_apple_create_readiness import DEFAULT_API_BASE_URL, load_env_file


PROFILE_PLATFORM_HINTS: tuple[tuple[str, str], ...] = (
    ("tvos", "tvOS"),
    ("appletv", "tvOS"),
    ("ipados", "iPad"),
    ("ipad", "iPad"),
    ("iphone", "iPhone"),
)


def platform_for_profile(profile: str) -> str | None:
    normalized = profile.strip().lower().replace("_", "-")
    if not normalized:
        return None
    for prefix, platform in PROFILE_PLATFORM_HINTS:
        if normalized == prefix or normalized.startswith(f"{prefix}-"):
            return platform
    return None


def load_journey_platforms(journey_src: Path) -> list[str]:
    payload = json.loads(journey_src.read_text(encoding="utf-8"))
    platforms = payload.get("platforms")
    if not isinstance(platforms, list):
        return []
    return [str(platform).strip() for platform in platforms if str(platform).strip()]


def validate_journey_profile_compatibility(journey_src: Path, profile: str) -> None:
    platform = platform_for_profile(profile)
    if platform is None:
        return
    journey_platforms = load_journey_platforms(journey_src)
    if not journey_platforms:
        return
    allowed = {candidate.lower() for candidate in journey_platforms}
    if platform.lower() in allowed:
        return
    raise ValueError(
        f"profile {profile!r} resolves to {platform}, but journey {journey_src} "
        f"is scoped to {', '.join(journey_platforms)}"
    )


def is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_auth_token(file_values: dict[str, str]) -> str:
    return (
        os.environ.get("E2E_AUTH_TOKEN")
        or os.environ.get("EBOOKTOOLS_SESSION_TOKEN")
        or file_values.get("E2E_AUTH_TOKEN")
        or file_values.get("EBOOKTOOLS_SESSION_TOKEN", "")
    )


def resolve_config(env_file: Path, *, profile: str = "") -> dict[str, object]:
    file_values = load_env_file(env_file)
    return {
        "profile": profile,
        "username": os.environ.get("E2E_USERNAME") or file_values.get("E2E_USERNAME", ""),
        "password": os.environ.get("E2E_PASSWORD") or file_values.get("E2E_PASSWORD", ""),
        "auth_token": resolve_auth_token(file_values),
        "api_base_url": (
            os.environ.get("E2E_API_BASE_URL")
            or file_values.get("E2E_API_BASE_URL")
            or DEFAULT_API_BASE_URL
        ),
        "allow_restored_session": is_truthy(
            os.environ.get("E2E_ALLOW_RESTORED_SESSION")
            or file_values.get("E2E_ALLOW_RESTORED_SESSION", "")
        ),
    }


def write_config_and_journey(
    *,
    env_file: Path,
    profile: str = "",
    config_path: Path,
    journey_src: Path,
    journey_path: Path,
    fallback_config_path: Path | None = None,
    fallback_journey_path: Path | None = None,
) -> dict[str, object]:
    resolved_profile = profile or config_path.parent.name
    validate_journey_profile_compatibility(journey_src, resolved_profile)
    config = resolve_config(env_file, profile=resolved_profile)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    journey_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    shutil.copyfile(journey_src, journey_path)
    if fallback_config_path and fallback_config_path != config_path:
        fallback_config_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_config_path.write_text(json.dumps(config), encoding="utf-8")
    if fallback_journey_path and fallback_journey_path != journey_path:
        fallback_journey_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(journey_src, fallback_journey_path)
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env", help="Path to optional .env file")
    parser.add_argument("--profile", default="", help="Requested E2E profile name for diagnostics")
    parser.add_argument("--config-path", required=True, help="Output JSON config path")
    parser.add_argument("--journey-src", required=True, help="Source journey JSON path")
    parser.add_argument("--journey-path", required=True, help="Output journey JSON path")
    parser.add_argument("--fallback-config-path", help="Optional platform-default config path to mirror")
    parser.add_argument("--fallback-journey-path", help="Optional platform-default journey path to mirror")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        write_config_and_journey(
            env_file=Path(args.env_file),
            profile=args.profile,
            config_path=Path(args.config_path),
            journey_src=Path(args.journey_src),
            journey_path=Path(args.journey_path),
            fallback_config_path=Path(args.fallback_config_path) if args.fallback_config_path else None,
            fallback_journey_path=Path(args.fallback_journey_path) if args.fallback_journey_path else None,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Apple E2E config write failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
