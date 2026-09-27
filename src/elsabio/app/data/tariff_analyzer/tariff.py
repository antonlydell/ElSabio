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
from elsabio.exceptions import ElSabioError
from elsabio.models.tariff_analyzer import TariffDataFrameModel


class _LoadFailedError(ElSabioError):
    r"""Raised by a cached loader so that a failed load is never cached.

    It never leaves this module: :func:`load_tariffs` turns it back into the
    ``(model, result)`` convention of :class:`elsabio.core.OperationResult`.
    Raising is the only way to keep a return value out of the data cache of
    Streamlit, which does not cache an exception.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset returned by the failed load.

    result : elsabio.core.OperationResult
        The result of the failed load.
    """

    def __init__(self, model: TariffDataFrameModel, result: OperationResult) -> None:
        super().__init__(message=result.short_msg, data=(model, result))
        self.model = model
        self.result = result


@st.cache_data(show_spinner='Loading tariffs ...')
def _load_tariffs(_session: Session) -> tuple[TariffDataFrameModel, OperationResult]:
    r"""Load the tariffs and cache only a successful load.

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

    Raises
    ------
    _LoadFailedError
        If the tariffs could not be loaded. The cache does not keep an exception.
    """

    model, result = load_tariff_model(session=_session)

    if not result.ok:
        raise _LoadFailedError(model=model, result=result)

    return model, result


def load_tariffs(session: Session) -> tuple[TariffDataFrameModel, OperationResult]:
    r"""Load the tariffs available to work with.

    A successful load is cached until it is cleared by :func:`clear_tariffs`, which the
    save path of an operation that writes a tariff calls. A failed load is never cached,
    so the next call tries the database again.

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

    try:
        return _load_tariffs(_session=session)
    except _LoadFailedError as e:
        return e.model, e.result


def clear_tariffs() -> None:
    r"""Clear the cached tariffs so that the next load reads them from the database.

    Call it from the save path of an operation that writes a tariff.
    """

    _load_tariffs.clear()
