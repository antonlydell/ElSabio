# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The models of the core database tables."""

# Local
from .default import add_default_core_models_to_session
from .models import (
    AuditColumnsMixin,
    Base,
    Currency,
    CustomRole,
    Email,
    MoneyPrice,
    MoneyTotal,
    Ratio,
    Role,
    SerieType,
    Unit,
    User,
    UserSignIn,
)

# The Public API
__all__ = [
    # default
    'add_default_core_models_to_session',
    # models
    'AuditColumnsMixin',
    'Base',
    'Currency',
    'CustomRole',
    'Email',
    'MoneyPrice',
    'MoneyTotal',
    'Ratio',
    'Role',
    'SerieType',
    'Unit',
    'User',
    'UserSignIn',
]
