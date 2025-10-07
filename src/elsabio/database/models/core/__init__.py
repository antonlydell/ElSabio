# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The models of the core database tables."""

# Local
from .default import add_default_core_models_to_session
from .models import (
    Base,
    Currency,
    CustomRole,
    Email,
    ModifiedAndCreatedColumnMixin,
    MoneyPrice,
    MoneyTotal,
    Ratio,
    Role,
    Unit,
    User,
    UserSignIn,
)

# The Public API
__all__ = [
    # default
    'add_default_core_models_to_session',
    # models
    'Base',
    'Currency',
    'CustomRole',
    'Email',
    'ModifiedAndCreatedColumnMixin',
    'MoneyPrice',
    'MoneyTotal',
    'Ratio',
    'Role',
    'Unit',
    'User',
    'UserSignIn',
]
