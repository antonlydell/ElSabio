# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The business logic for customer group related operations of the Tariff Analyzer module."""

# Local
from .map_facilities import (
    create_facility_customer_group_link_upsert_dataframes,
    map_facilities_to_customer_groups,
    validate_duplicate_facility_customer_group_links,
    validate_facility_customer_group_input_data_models,
)

# The Public API
__all__ = [
    # map_facilities
    'create_facility_customer_group_link_upsert_dataframes',
    'map_facilities_to_customer_groups',
    'validate_duplicate_facility_customer_group_links',
    'validate_facility_customer_group_input_data_models',
]
