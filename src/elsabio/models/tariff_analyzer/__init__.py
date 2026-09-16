# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The data models of the Tariff Analyzer module."""

# Local
from .customer_group import (
    CustomerGroupDataFrameModel,
    CustomerGroupMappingStrategyEnum,
    FacilityCustomerGroupLinkDataFrameModel,
)
from .facility import (
    FacilityDataFrameModel,
    FacilityImportDataFrameModel,
    FacilityMappingDataFrameModel,
    FacilityTypeEnum,
    FacilityTypeMappingDataFrameModel,
)
from .facility_contract import (
    CustomerTypeEnum,
    CustomerTypeMappingDataFrameModel,
    FacilityContractDataFrameModel,
    FacilityContractExtendedDataFrameModel,
    FacilityContractImportDataFrameModel,
    FacilityContractMappingDataFrameModel,
)
from .product import (
    ProductDataFrameModel,
    ProductImportDataFrameModel,
    ProductMappingDataFrameModel,
)
from .serie_value import SerieValueDataFrameModel, SerieValueImportDataFrameModel
from .tariff import (
    CUSTOMER_GROUP_ID_DTYPE,
    DATE_ID_DTYPE,
    FACILITY_ID_DTYPE,
    SERIE_VALUE_DTYPE,
    TARIFF_COMPONENT_ID_DTYPE,
    TARIFF_COMPONENT_TYPE_ID_DTYPE,
    TARIFF_COST_GROUP_ID_DTYPE,
    TARIFF_ID_DTYPE,
    TARIFF_PRICE_DTYPE,
    TARIFF_VALUE_DTYPE,
    CalcStrategyEnum,
    PeriodizeStrategyEnum,
    TariffCalculationDataFrameModel,
    TariffCalculationExtendedDataFrameModel,
    TariffDataFrameModel,
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
)

# The Public API
__all__ = [
    # customer_group
    'CustomerGroupDataFrameModel',
    'CustomerGroupMappingStrategyEnum',
    'FacilityCustomerGroupLinkDataFrameModel',
    # facility
    'FacilityDataFrameModel',
    'FacilityImportDataFrameModel',
    'FacilityMappingDataFrameModel',
    'FacilityTypeEnum',
    'FacilityTypeMappingDataFrameModel',
    # facility_contract
    'CustomerTypeEnum',
    'CustomerTypeMappingDataFrameModel',
    'FacilityContractDataFrameModel',
    'FacilityContractExtendedDataFrameModel',
    'FacilityContractImportDataFrameModel',
    'FacilityContractMappingDataFrameModel',
    # product
    'ProductDataFrameModel',
    'ProductImportDataFrameModel',
    'ProductMappingDataFrameModel',
    # serie_value
    'SerieValueDataFrameModel',
    'SerieValueImportDataFrameModel',
    # tariff
    'CUSTOMER_GROUP_ID_DTYPE',
    'DATE_ID_DTYPE',
    'FACILITY_ID_DTYPE',
    'SERIE_VALUE_DTYPE',
    'TARIFF_COMPONENT_ID_DTYPE',
    'TARIFF_COMPONENT_TYPE_ID_DTYPE',
    'TARIFF_COST_GROUP_ID_DTYPE',
    'TARIFF_ID_DTYPE',
    'TARIFF_PRICE_DTYPE',
    'TARIFF_VALUE_DTYPE',
    'CalcStrategyEnum',
    'PeriodizeStrategyEnum',
    'TariffCalculationDataFrameModel',
    'TariffCalculationExtendedDataFrameModel',
    'TariffDataFrameModel',
    'TariffValueFacilityDataFrameModel',
    'TariffValueTotalDataFrameModel',
]
