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
def load_tariffs(_session: Session) -> tuple[TariffDataFrameModel, OperationResult]:
    r"""Load the tariffs available to work with.

    The result is cached until it is cleared by the save path of an operation
    that writes a tariff, e.g. ``load_tariffs.clear()``.

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
