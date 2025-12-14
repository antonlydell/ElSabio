# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Functions to perform CREATE, READ, UPDATE and DELETE operations for Tariff Analyzer."""

# Local
from .facility import bulk_insert_facilities, bulk_update_facilities, load_facility_mapping_model
from .facility_type import load_facility_type_mapping_model

# The Public API
__all__ = [
    # facility
    'bulk_insert_facilities',
    'bulk_update_facilities',
    'load_facility_mapping_model',
    # facility_type
    'load_facility_type_mapping_model',
]
