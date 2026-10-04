# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Cached loaders of the reference data of the app.

The loaders rely on the Streamlit caching mechanisms. A loader should clear
its own cache on a failed load. The cache is expected to be cleared
explicitly by the save path that writes the data model in question.
"""
