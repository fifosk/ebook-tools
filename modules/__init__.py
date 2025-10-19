"""Shared modules package for ebook-tools."""

from .environment import load_environment

# Load environment variables from .env-style files as soon as the package is
# imported. This keeps CLI entry points and the FastAPI app in sync when running
# locally or in deployment-specific environments.
load_environment()

__all__ = ["load_environment"]
