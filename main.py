#!/usr/bin/env python3
"""Lightweight entry point for the ebook tools pipeline."""

from modules.ebook_tools import run_pipeline as _run_pipeline

__all__ = ["run_pipeline"]


def run_pipeline():
    """Delegate to the packaged pipeline implementation."""
    return _run_pipeline()


if __name__ == "__main__":
    run_pipeline()
