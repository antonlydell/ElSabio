# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Cached loaders of the reference data of the Tariff Analyzer module."""

# Local
from .tariff import load_tariffs

# The Public API
__all__ = [
    # tariff
    'load_tariffs',
]
