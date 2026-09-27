# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Cached loaders of the tariff reference data."""

# Third party
import streamlit as st

# Local
from elsabio.core import OperationResult
from elsabio.database import Session
from elsabio.database.tariff_analyzer import load_tariff_model
from elsabio.models.tariff_analyzer import TariffDataFrameModel


@st.cache_data(show_spinner='Loading tariffs ...')
def _load_tariffs(_session: Session) -> tuple[TariffDataFrameModel, OperationResult]:
    r"""Load the tariffs and cache the result.

    Parameters
    ----------
    _session : elsabio.db.Session
        An active database session. Not part of the cache key.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs.

    result : elsabio.core.OperationResult
        The result of loading the tariffs from the database.
    """

    return load_tariff_model(session=_session)


def load_tariffs(session: Session) -> tuple[TariffDataFrameModel, OperationResult]:
    r"""Load the tariffs available to work with.

    A successful load is cached until it is cleared by :func:`clear_tariffs`, which the
    save path of an operation that writes a tariff calls. A failed load is cleared from
    the cache straight away, so the next call tries the database again.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session. Not part of the cache key.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs.

    result : elsabio.core.OperationResult
        The result of loading the tariffs from the database.
    """

    model, result = _load_tariffs(_session=session)

    if not result.ok:
        clear_tariffs()

    return model, result


def clear_tariffs() -> None:
    r"""Clear the cached tariffs so that the next load reads them from the database.

    Call it from the save path of an operation that writes a tariff.
    """

    _load_tariffs.clear()
