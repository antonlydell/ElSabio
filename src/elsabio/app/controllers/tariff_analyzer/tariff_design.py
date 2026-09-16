# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The controller of the Tariff Design page."""

# Local
from elsabio.app.components import operation_error
from elsabio.app.data.tariff_analyzer import load_tariffs
from elsabio.app.views.tariff_analyzer import tariff_design as views
from elsabio.database import Session


def controller(session: Session) -> None:
    r"""Render the Tariff Design page.

    The selected tariff and the active tab are carried in the address of the page,
    by the views that own them, which makes the page linkable and survivable across
    a browser refresh.

    Parameters
    ----------
    session : elsabio.db.Session
        An active session to the ElSabio database.
    """

    views.title()

    model, result = load_tariffs(_session=session)

    if not result.ok:
        load_tariffs.clear()  # Do not serve a failed load from the cache.
        operation_error(result)
        return

    if model.empty:
        views.explainer(expanded=True)
        views.no_tariffs_defined()
        return

    views.explainer()
    views.tariff_list(model=model)
    views.select_tariff(model=model)
    views.tariff_tabs()
