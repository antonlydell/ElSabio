# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The core database tables."""

# Standard library
from typing import ClassVar

# Third party
from sqlalchemy import Identity, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from streamlit_passwordless.database.models import AuditColumnsMixin as AuditColumnsMixin
from streamlit_passwordless.database.models import Base as Base
from streamlit_passwordless.database.models import CustomRole as CustomRole
from streamlit_passwordless.database.models import Email as Email
from streamlit_passwordless.database.models import Role as Role
from streamlit_passwordless.database.models import User as User
from streamlit_passwordless.database.models import UserSignIn as UserSignIn

MoneyTotal = Numeric(20, 3)  # Currency in totals (milli-minor unit precision)
MoneyPrice = Numeric(20, 6)  # Currency per unit (e.g., per SEK/kWh)
Ratio = Numeric(9, 6)  # Ratios like reactive power / active power


class Currency(AuditColumnsMixin, Base):
    r"""The currencies of the application.

    Parameters
    ----------
    currency_id : int
        The unique ID of the currency. The primary key of the table.

    iso_code : str
        The ISO code of the currency. Must be unique. Is indexed.

    name : str
        The name of the currency.

    minor_unit_name : str
        The name of the minor unit of the currency e.g. öre.

    minor_per_major : int
        The number of minor units that make up one major unit of the currency.
        E.g. 100 öre = 1 SEK.

    display_decimals : int, default 2
        The number of decimals to display for the currency.

    symbol : str
        The symbol of the currency.

    symbol_minor_unit : str or None
        The symbol of the minor unit of the currency.

    description : str or None
        A description of the currency.

    updated_at : datetime.datetime or None
        The timestamp at which the currency was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the currency.

    created_at : datetime.datetime
        The timestamp at which the currency was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the currency.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'currency_id',
        'iso_code',
        'name',
        'minor_unit_name',
        'minor_per_major',
        'display_decimals',
        'symbol',
        'symbol_minor_unit',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'currency'

    currency_id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    iso_code: Mapped[str]
    name: Mapped[str]
    minor_unit_name: Mapped[str]
    minor_per_major: Mapped[int]
    display_decimals: Mapped[int] = mapped_column(server_default='2')
    symbol: Mapped[str | None]
    symbol_minor_unit: Mapped[str | None]
    description: Mapped[str | None]


Index(f'{Currency.__tablename__}_iso_code_uix', Currency.iso_code, unique=True)


class Unit(AuditColumnsMixin, Base):
    r"""The units of the application.

    Parameters
    ----------
    unit_id : int
        The unique ID of the unit. The primary key of the table.

    code : str
        The code of the unit. Must be unique. Is indexed.

    display_name : str
        The display name of the unit.

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
        'code',
        'display_name',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'unit'

    unit_id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    code: Mapped[str]
    display_name: Mapped[str]
    description: Mapped[str | None]


Index(f'{Unit.__tablename__}_code_uix', Unit.code, unique=True)


class SerieType(AuditColumnsMixin, Base):
    r"""The types of meter data series.

    Parameters
    ----------
    serie_type_id : int
        The unique ID of the serie type. The primary key of the table.

    name : str
        The unique name of the serie type. Is indexed.

    external_id : str or None
        The unique external ID of the serie type. Is indexed.

    description : str or None
        A description of the serie type.

    updated_at : datetime.datetime or None
        The timestamp at which the serie type was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the serie type.

    created_at : datetime.datetime
        The timestamp at which the serie type was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the serie type.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'currency_id',
        'name',
        'external_id',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'serie_type'

    serie_type_id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str]
    external_id: Mapped[str | None]
    description: Mapped[str | None]


Index(f'{SerieType.__tablename__}_name_uix', SerieType.name, unique=True)
Index(f'{SerieType.__tablename__}_external_id_uix', SerieType.external_id, unique=True)
