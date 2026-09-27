# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The controller of the Tariff Design page."""

# Standard library
from zoneinfo import ZoneInfo

# Local
from elsabio.app.components import operation_error
from elsabio.app.data.tariff_analyzer import load_tariffs
from elsabio.app.views.tariff_analyzer.tariff_design import (
    explainer,
    no_tariffs_defined,
    select_tariff,
    tariff_list,
    tariff_tabs,
    title,
)
from elsabio.database import Session


def controller(session: Session, timezone: ZoneInfo) -> None:
    r"""Render the Tariff Design page.

    The selected tariff and the active tab are carried in the address of the page,
    by the views that own them, which makes the page linkable and survivable across
    a browser refresh.

    Parameters
    ----------
    session : elsabio.db.Session
        An active session to the ElSabio database.

    timezone : zoneinfo.ZoneInfo
        The configured business timezone of the app.
    """

    title()

    model, result = load_tariffs(session=session)

    if not result.ok:
        operation_error(result)
        return

    if model.empty:
        explainer(expanded=True)
        no_tariffs_defined()
        return

    explainer()
    tariff_list(model=model, timezone=timezone)
    select_tariff(model=model)
    tariff_tabs()
