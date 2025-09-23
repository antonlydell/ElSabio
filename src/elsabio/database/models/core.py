# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The core database tables."""

# Standard library
from typing import ClassVar

# Third party
from sqlalchemy import Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from streamlit_passwordless.database.models import Base as Base
from streamlit_passwordless.database.models import CustomRole as CustomRole
from streamlit_passwordless.database.models import Email as Email
from streamlit_passwordless.database.models import (
    ModifiedAndCreatedColumnMixin as ModifiedAndCreatedColumnMixin,
)
from streamlit_passwordless.database.models import Role as Role
from streamlit_passwordless.database.models import User as User
from streamlit_passwordless.database.models import UserSignIn as UserSignIn

MoneyTotal = Numeric(20, 3)  # Currency in totals (milli-minor unit precision)
MoneyPrice = Numeric(20, 6)  # Currency per unit (e.g., per kWh/kW/month)
Ratio = Numeric(9, 6)  # For ratios like the reactive / active power is allowed to be 0.75.


class Currency(ModifiedAndCreatedColumnMixin, Base):
    r"""The currencies of the application.

    Parameters
    ----------
    unit_id : int
        The unique ID of the unit. The primary key of the table.

    name : str
        The name of the unit. Must be unique. Is indexed.

    description : str or None
        A description of the unit.

    updated_at : datetime.datetime or None
        The timestamp at which the unit was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the unit.

    created_at : datetime.datetime
        The timestamp at which the unit was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the unit.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'unit_id',
        'name',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'currency'

    currency_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    iso_code: Mapped[str]
    name: Mapped[str]
    minor_unit_name: Mapped[str]
    minor_per_major: Mapped[int]
    display_decimals: Mapped[int] = mapped_column(server_default='2')
    description: Mapped[str | None]


Index(f'{Currency.__tablename__}_code_uix', Currency.code, unique=True)


class Unit(ModifiedAndCreatedColumnMixin, Base):
    r"""The units of the application.

    Parameters
    ----------
    unit_id : int
        The unique ID of the unit. The primary key of the table.

    display_name : str
        The name of the unit. Must be unique. Is indexed.

    description : str or None
        A description of the unit.

    updated_at : datetime.datetime or None
        The timestamp at which the unit was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the unit.

    created_at : datetime.datetime
        The timestamp at which the unit was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the unit.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'unit_id',
        'name',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'unit'

    unit_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str]
    display_name: Mapped[str]
    description: Mapped[str | None]


Index(f'{Unit.__tablename__}_name_uix', Unit.code, unique=True)
