# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Functions for working with the `Tariff` related models of Tariff Analyzer."""

# Standard library
import logging
from collections.abc import Sequence
from datetime import date

# Third party
from sqlalchemy import and_, case, extract, or_, select
from sqlalchemy.orm import aliased

# Local
from elsabio.core import OperationResult
from elsabio.database.core import (
    Session,
    SQLAlchemyError,
    load_sql_query_as_dataframe,
)
from elsabio.database.models.core import SerieType
from elsabio.database.models.tariff_analyzer import (
    CalcStrategy,
    CustomerGroup,
    Facility,
    FacilityContract,
    FacilityCustomerGroupLink,
    PeriodizeStrategy,
    Tariff,
    TariffComponent,
    TariffComponentType,
    TariffCostGroup,
    TariffCostGroupCustomerGroupLink,
)
from elsabio.models.tariff_analyzer import (
    TariffCalculationDataFrameModel,
)

logger = logging.getLogger(__name__)


def load_tariff_ids(
    session: Session, tariff_ids: Sequence[int] | None = None, check_all_loaded: bool = True
) -> tuple[tuple[int, ...], OperationResult]:
    r"""Load the tariff_id:s of the available tariffs.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    tariff_ids : Sequence[int] or None, default None
        The primary keys of the tariffs to load. If None all tariffs are loaded.

    check_all_loaded : bool, default True
        If True check that all tariff_id:s present in `tariff_ids` were loaded
        from the Database and False to omit this validation.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.CustomerGroupDataFrameModel
        The loaded tariff_id:s.

    result : elsabio.core.OperationResult
        The result of loading the tariff_id:s from the database.
    """

    query = select(Tariff.tariff_id).order_by(Tariff.tariff_id.asc())

    if tariff_ids:
        query = query.where(Tariff.tariff_id.in_(tariff_ids))

    try:
        loaded_tariff_ids = session.execute(query).scalars().all()
    except SQLAlchemyError as e:
        error_msg = 'Error loading tariff_id:s for the database!'
        long_msg = f'{error_msg}\n{e!s}' if error_msg else str(e)
        logger.exception(long_msg)
        result = OperationResult(
            ok=False,
            short_msg=error_msg,
            long_msg=long_msg,
            code=f'{e.__module__}.{e.__class__.__name__}',
        )
        return (), result

    result = OperationResult(ok=True)

    if check_all_loaded and tariff_ids is not None:
        diff = set(tariff_ids).difference(set(loaded_tariff_ids))
        if diff:
            result = OperationResult(
                ok=False, short_msg=f'Tariffs with tariff_id:s {tuple(sorted(diff))} do not exist!'
            )

    return tuple(loaded_tariff_ids), result


def load_tariff_calculation_model(
    session: Session, tariff_ids: Sequence[int], start_date: date, end_date: date | None = None
) -> tuple[TariffCalculationDataFrameModel, OperationResult]:
    r"""Load the data model with the input data to the tariff calculations.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    start_date : datetime.date
        The start date of the interval in which to load the
        tariff calculation dataset (inclusive).

    end_date : datetime.date or None
        The end date of the interval in which to load the tariff calculation
        dataset (exclusive). If None the interval is open and unbounded.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel
        The tariff calculation dataset.

    result : elsabio.core.OperationResult
        The result of loading the tariff calculation dataset from the database.
    """

    if end_date is None:
        where_clause = FacilityCustomerGroupLink.date_id >= start_date
    else:
        where_clause = and_(
            FacilityCustomerGroupLink.date_id >= start_date,
            FacilityCustomerGroupLink.date_id < end_date,
        )

    where_clause = and_(where_clause, Tariff.tariff_id.in_(tariff_ids))

    comparison_serie_type = aliased(SerieType)

    validity_start = TariffComponent.validity_start
    validity_end = TariffComponent.validity_end

    month_id = extract('month', FacilityContract.date_id)

    in_validity = or_(
        and_(validity_start <= validity_end, month_id.between(validity_start, validity_end)),
        and_(
            validity_start > validity_end, or_(month_id >= validity_start, month_id <= validity_end)
        ),
    )
    total_price_outside_validity = (
        TariffComponent.price_outside_validity + TariffComponent.authority_fee_outside_validity
    )

    total_price = case(
        (in_validity, TariffComponent.price + TariffComponent.authority_fee),
        else_=total_price_outside_validity,
    )
    price = case(
        (in_validity, TariffComponent.price),
        else_=TariffComponent.price_outside_validity,
    )
    authority_fee = case(
        (in_validity, TariffComponent.authority_fee),
        else_=TariffComponent.authority_fee_outside_validity,
    )

    query = (
        select(
            Facility.facility_id.label(TariffCalculationDataFrameModel.c_facility_id),
            FacilityContract.date_id.label(TariffCalculationDataFrameModel.c_date_id),
            Tariff.tariff_id.label(TariffCalculationDataFrameModel.c_tariff_id),
            TariffCostGroup.tariff_cost_group_id.label(
                TariffCalculationDataFrameModel.c_tariff_cost_group_id
            ),
            CustomerGroup.customer_group_id.label(
                TariffCalculationDataFrameModel.c_customer_group_id
            ),
            TariffComponentType.tariff_component_type_id.label(
                TariffCalculationDataFrameModel.c_tariff_component_type_id
            ),
            TariffComponent.tariff_component_id.label(
                TariffCalculationDataFrameModel.c_tariff_component_id
            ),
            CalcStrategy.code.label(TariffCalculationDataFrameModel.c_calc_strategy_code),
            PeriodizeStrategy.code.label(TariffCalculationDataFrameModel.c_periodize_strategy_code),
            total_price.label(TariffCalculationDataFrameModel.c_total_price),
            price.label(TariffCalculationDataFrameModel.c_price),
            authority_fee.label(TariffCalculationDataFrameModel.c_authority_fee),
            FacilityContract.subscribed_power.label(
                TariffCalculationDataFrameModel.c_subscribed_power
            ),
            FacilityContract.connection_power.label(
                TariffCalculationDataFrameModel.c_connection_power
            ),
            SerieType.code.label(TariffCalculationDataFrameModel.c_serie_type_code),
            comparison_serie_type.code.label(
                TariffCalculationDataFrameModel.c_comparison_serie_type_code
            ),
            TariffComponent.overshoot_limit.label(
                TariffCalculationDataFrameModel.c_overshoot_limit
            ),
        )
        .select_from(Tariff)
        .join(Tariff.tariff_cost_groups)
        .join(TariffCostGroup.tariff_components)
        .join(TariffComponent.tariff_component_type)
        .join(TariffComponentType.calc_strategy)
        .join(TariffComponentType.periodize_strategy)
        .join(TariffCostGroup.tariff_cost_group_customer_group_links)
        .join(TariffCostGroupCustomerGroupLink.customer_group)
        .join(CustomerGroup.facility_customer_group_links)
        .join(FacilityCustomerGroupLink.facility)
        .join(
            FacilityContract,
            onclause=and_(
                FacilityContract.facility_id == FacilityCustomerGroupLink.facility_id,
                FacilityContract.date_id == FacilityCustomerGroupLink.date_id,
            ),
        )
        .join(TariffComponentType.serie_type, isouter=True)
        .join(comparison_serie_type, TariffComponentType.comparison_serie_type, isouter=True)
        .where(where_clause)
        .order_by(
            FacilityContract.date_id.asc(),
            Facility.facility_id.asc(),
            TariffComponentType.tariff_component_type_id.asc(),
            Tariff.tariff_id.asc(),
            TariffCostGroup.tariff_cost_group_id.asc(),
            CustomerGroup.customer_group_id.asc(),
        )
    )

    df, result = load_sql_query_as_dataframe(
        query=query,
        session=session,
        dtypes={},
        parse_dates=TariffCalculationDataFrameModel.parse_dates,
        error_msg='Error loading tariff calculation model from the database!',
    )

    return TariffCalculationDataFrameModel(df=df), result
