"""Compatibility re-export for constants.

The prototype still keeps constants in the top-level ``config`` module. This
file lets newer code import ``core.config`` without splitting the project yet.
"""

from config import *  # noqa: F401,F403
