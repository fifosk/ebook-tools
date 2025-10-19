"""CLI adapters for orchestrating the ebook-tools pipeline."""

__all__ = ["run_pipeline"]

from .menu import run_pipeline  # re-export for convenience
