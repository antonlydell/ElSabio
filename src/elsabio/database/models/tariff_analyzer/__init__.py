# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The database models of the Tariff Analyzer module."""

# Local
from .default import add_default_tariff_analyzer_models_to_session
from .models import (
    CalcStrategy,
    CustomerGroup,
    CustomerGroupMappingStrategy,
    CustomerType,
    Facility,
    FacilityContract,
    FacilityCustomerGroupLink,
    FacilityType,
    Product,
    Tariff,
    TariffComponent,
    TariffComponentType,
    TariffCostGroup,
    TariffCostGroupCustomerGroupLink,
    TariffTariffComponentTypeLink,
)

# The Public API
__all__ = [
    # default
    'add_default_tariff_analyzer_models_to_session',
    # models
    'CalcStrategy',
    'CustomerGroup',
    'CustomerGroupMappingStrategy',
    'CustomerType',
    'Facility',
    'FacilityContract',
    'FacilityCustomerGroupLink',
    'FacilityType',
    'Product',
    'Tariff',
    'TariffComponent',
    'TariffComponentType',
    'TariffCostGroup',
    'TariffCostGroupCustomerGroupLink',
    'TariffTariffComponentTypeLink',
]
