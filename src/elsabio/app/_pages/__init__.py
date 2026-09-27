# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The pages of the ElSabio web app."""

# Standard library
from enum import StrEnum

# Local
from elsabio.app.auth import Role, SuperUserRole


class Pages(StrEnum):
    r"""The pages of the application."""

    INIT = '_pages/init.py'
    HOME = '_pages/home.py'
    SIGN_IN = '_pages/sign_in.py'
    TARIFF_DESIGN = '_pages/tariff_analyzer/tariff_design.py'


# The role required to use a gated page. A user of a role of higher rank may use it too.
# The router shows a gated page in the navigation only to a user who may use it and the
# page guards its entry point with the same role, so the two cannot disagree.
REQUIRED_ROLES: dict[Pages, Role] = {
    Pages.TARIFF_DESIGN: SuperUserRole,
}
