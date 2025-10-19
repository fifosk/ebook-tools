#!/usr/bin/env python3
"""Deprecated module retained for backward compatibility."""

from __future__ import annotations

from .adapters.cli.menu import run_pipeline

__all__ = ["run_pipeline"]


if __name__ == "__main__":
    run_pipeline()
