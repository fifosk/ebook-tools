#!/usr/bin/env python3
"""Lightweight entry point for the ebook tools pipeline."""

from modules import logging_manager as log_mgr
from modules.ebook_tools import run_pipeline as _run_pipeline

logger = log_mgr.get_logger()

__all__ = ["run_pipeline"]


def run_pipeline():
    """Delegate to the packaged pipeline implementation."""
    try:
        return _run_pipeline()
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user request. Cleaning up...")
        return None


if __name__ == "__main__":
    run_pipeline()
