# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Configuration for the test suite of ElSabio."""

# Standard library
from pathlib import Path

# =============================================================================================
# Constants
# =============================================================================================

TEST_DIR = Path(__file__).parent
STATIC_FILES_BASE_DIR = TEST_DIR / 'static_files'
STATIC_FILES_CONFIG_BASE_DIR = STATIC_FILES_BASE_DIR / 'config'
STATIC_FILES_TARIFF_ANALYZER_BASE_DIR = STATIC_FILES_BASE_DIR / 'tariff_analyzer'
