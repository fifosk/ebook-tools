"""Command line interface utilities for ebook-tools.

This package replaces the monolithic :mod:`modules.menu_interface` module.  The
submodules break down the historical responsibilities as follows:

* :mod:`modules.cli.args` builds the command line parser and translates legacy
  positional arguments into structured namespaces.
* :mod:`modules.cli.context` encapsulates runtime context refresh logic.  It
  centralises how configuration overrides flow into
  :func:`modules.config_manager.build_runtime_context` and how the active
  context is cached via :func:`modules.config_manager.set_runtime_context`.
* :mod:`modules.cli.interactive` implements the interactive prompt loop and
  delegates pipeline refreshes to :mod:`modules.cli.pipeline_runner`.
* :mod:`modules.cli.pipeline_runner` acts as the bridge between the CLI and the
  ingestion/pipeline subsystems.  It ensures that configuration derived from
  prompts is normalised before invoking :func:`modules.core.config.build_pipeline_config`.

Historically, the interactive session implicitly reloaded configuration after
updating directory overrides.  That flow now lives in
:func:`modules.cli.context.refresh_runtime_context` which updates the global
runtime context each time a mutating prompt executes.  Both the legacy menu
shim and the new ``ebook-tools`` console script call into the same helper
functions, keeping configuration and pipeline behaviour consistent regardless
of entry point.
"""

from . import args, context, interactive, pipeline_runner

__all__ = ["args", "context", "interactive", "pipeline_runner"]
