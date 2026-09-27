# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Cached loaders of the reference data of the app.

The loaders use the copying data cache of Streamlit so that the dataset handed to one
user cannot be mutated underneath another, and it is cleared explicitly by the save path
of an operation that writes the entity in question. The resource cache is not used here
since it hands every user the same object. Both caches are shared by all sessions of the
process. A loader owns its cache policy: it clears a failed load from the cache itself, so
no caller has to remember to clear it.
"""
