# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The database tables of the Tariff Analyzer module."""

# Standard library
from datetime import date, datetime
from typing import ClassVar

# Third party
from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local
from .core import Base, ModifiedAndCreatedColumnMixin, Unit


class FacilityType(ModifiedAndCreatedColumnMixin, Base):
    r"""The type of an electricity facility.

    Parameters
    ----------
    facility_type_id : int
        The unique ID of the facility type. The primary key of the table.

    name : str
        The name of the facility type. Must be unique. Is indexed.

    description : str or None
        A description of the facility type.

    updated_at : datetime.datetime or None
        The timestamp at which the facility type was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the facility type.

    created_at : datetime.datetime
        The timestamp at which the facility type was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the facility type.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'facility_type_id',
        'name',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_facility_type'

    facility_type_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None]
    description: Mapped[str | None]

    facilities: Mapped[list['Facility']] = relationship(back_populates='facility_type')


Index(f'{FacilityType.__tablename__}_name_uix', FacilityType.name, unique=True)


class Facility(ModifiedAndCreatedColumnMixin, Base):
    r"""A facility where electricity is delivered as part of a grid contract.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility. The primary key of the table.

    ean : int
        The unique EAN code of the facility. Must be unique. Is indexed.

    facility_type_id : int
        The type of facility. Foreign key to :attr:`FacilityType.facility_type_id`. Is indexed.

    name : str or None
        A descriptive name of the facility.

    description : str or None
        A description of the facility.

    updated_at : datetime.datetime or None
        The timestamp at which the facility was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the facility.

    created_at : datetime.datetime
        The timestamp at which the facility was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the facility.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'facility_id',
        'ean',
        'facility_type_id',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_facility'

    facility_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ean: Mapped[int] = mapped_column(BigInteger)
    facility_type_id: Mapped[int] = mapped_column(
        ForeignKey(FacilityType.facility_type_id), server_default=text('0')
    )
    name: Mapped[str | None]
    description: Mapped[str | None]

    facility_type: Mapped[FacilityType] = relationship(back_populates='facilities')
    facility_contracts: Mapped[list['FacilityContract']] = relationship(back_populates='facility')

    facility_customer_group_links: Mapped[list['FacilityCustomerGroupLink']] = relationship(
        back_populates='facility'
    )


Index(f'{Facility.__tablename__}_ean_uix', Facility.ean, unique=True)


class FacilityContract(ModifiedAndCreatedColumnMixin, Base):
    r"""Contract related information of a facility valid per month.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility. Part of the primary key of the table.

    date_id : datetime.date
        The month the contract data is valid for represented as the first day of the month in
        the configured business timezone of the app. Part of the primary key of the table.

    fuse_size : int or None
        The contracted fuse size [A].

    active_power_cons : float or None
        The contracted active power consumption [kW].

    active_power_prod : float or None
        The contracted active power production [kW].

    updated_at : datetime.datetime or None
        The timestamp at which the facility contract was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the facility contract.

    created_at : datetime.datetime
        The timestamp at which the facility contract was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the facility contract.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'facility_id',
        'date_id',
        'fuse_size',
        'active_power_cons',
        'active_power_prod',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_facility_contract'

    facility_id: Mapped[int] = mapped_column(ForeignKey(Facility.facility_id), primary_key=True)
    date_id: Mapped[date] = mapped_column(
        primary_key=True,
        comment=(
            'The month the contract data is valid for represented as the first day of the month in '
            'the configured business timezone of the app. Part of the primary key of the table.'
        ),
    )
    fuse_size: Mapped[int | None]
    active_power_cons: Mapped[float | None]
    active_power_prod: Mapped[float | None]

    facility: Mapped[Facility] = relationship(back_populates='facility_contracts')

    __table_args__ = (
        CheckConstraint(func.extract('day', date_id) == 1, name='ck_fc_date_id_first_of_month'),
    )


Index(
    f'{FacilityContract.__tablename__}_date_id__facility_id_ix',
    FacilityContract.date_id,
    FacilityContract.facility_id,
)


class CustomerGroup(ModifiedAndCreatedColumnMixin, Base):
    r"""A facility is part of a customer group based on its facility contract information.

    Parameters
    ----------
    customer_group_id : int
       The unique ID of the customer group. The primary key of the table.

    name : str
        The name of the customer group. Must be unique. Is indexed.

    fuse_size : int or None
        The fuse size [A] of the customer group.

    min_active_power_cons : float or None
        The minimum contracted active power consumption of the customer group.

    max_active_power_cons : float or None
        The maximum contracted active power consumption of the customer group.

    description : str or None
        A description of the customer group.

    updated_at : datetime.datetime or None
        The timestamp at which the customer group was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the customer group.

    created_at : datetime.datetime
        The timestamp at which the customer group was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the customer group.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'customer_group_id',
        'name',
        'fuse_size',
        'min_active_power_cons',
        'max_active_power_cons',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_customer_group'

    customer_group_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    fuse_size: Mapped[int | None]
    min_active_power_cons: Mapped[float | None]
    max_active_power_cons: Mapped[float | None]
    description: Mapped[str | None]

    facility_customer_group_links: Mapped[list['FacilityCustomerGroupLink']] = relationship(
        back_populates='customer_group'
    )
    tariff_cost_group_customer_group_links: Mapped[list['TariffCostGroupCustomerGroupLink']] = (
        relationship(back_populates='customer_group')
    )


Index(f'{CustomerGroup.__tablename__}_name_uix', CustomerGroup.name, unique=True)


class FacilityCustomerGroupLink(ModifiedAndCreatedColumnMixin, Base):
    r"""The link between a facility and customer group.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility. Part of the primary key.
        Foreign key to :attr:`Facility.facility_id`. Is indexed.

    date_id : datetime.date
        The month the link is valid for represented as the first day of the month in the
        configured business timezone of the app. Part of the primary key.

    customer_group_id : int
        The unique ID of the customer group the facility is part of.
        Foreign key to :attr:`CustomerGroup.customer_group_id`. Is indexed.

    updated_at : datetime.datetime or None
        The timestamp at which the facility customer group link was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the facility customer group link.

    created_at : datetime.datetime
        The timestamp at which the facility customer group link was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the facility customer group link.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'facility_id',
        'date_id',
        'customer_group_id',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_facility_customer_group_link'

    facility_id: Mapped[int] = mapped_column(ForeignKey(Facility.facility_id), primary_key=True)
    date_id: Mapped[datetime] = mapped_column(
        Date,
        primary_key=True,
        comment=(
            'The month the link is valid for represented as the first day of the '
            'month in the configured business timezone of the app.'
        ),
    )
    customer_group_id: Mapped[int] = mapped_column(ForeignKey(CustomerGroup.customer_group_id))

    facility: Mapped[Facility] = relationship(back_populates='facility_customer_group_links')
    customer_group: Mapped[CustomerGroup] = relationship(
        back_populates='facility_customer_group_links'
    )

    __table_args__ = (
        CheckConstraint(
            func.extract('day', date_id) == 1, name='ck_fcg_link_date_id_first_of_month'
        ),
    )


Index(
    'ta_facility_cg_link_ts_id__cg_id_ix',
    FacilityCustomerGroupLink.date_id,
    FacilityCustomerGroupLink.customer_group_id,
)


class Tariff(ModifiedAndCreatedColumnMixin, Base):
    r"""An electricity tariff.

    Parameters
    ----------
    tariff_id : int
        The unique ID of the tariff. The primary key of the table.

    name : str
        The name of the tariff. Must be unique. Is indexed.

    validity_start : datetime.date or None
        The start date the tariff is valid from (inclusive)
        in the configured business timezone of the app.

    validity_end: datetime.date or None
        The end date the tariff is valid until (exclusive)
        in the configured business timezone of the app.

    description : str or None
        A description of the tariff.

    updated_at : datetime.datetime or None
        The timestamp at which the tariff was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the tariff.

    created_at : datetime.datetime
        The timestamp at which the tariff was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the tariff.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'tariff_id',
        'name',
        'validity_start',
        'validity_end',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_tariff'

    tariff_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    validity_start: Mapped[date | None] = mapped_column(
        Date,
        comment=(
            'The start date the tariff is valid from (inclusive) '
            'in the configured business timezone of the app.'
        ),
    )
    validity_end: Mapped[date | None] = mapped_column(
        Date,
        comment=(
            'The end date the tariff is valid until (exclusive) '
            'in the configured business timezone of the app.'
        ),
    )
    description: Mapped[str | None]

    tariff_cost_groups: Mapped['TariffCostGroup'] = relationship(back_populates='tariff')


Index(f'{Tariff.__tablename__}_name_uix', Tariff.name, unique=True)


class TariffCostGroup(ModifiedAndCreatedColumnMixin, Base):
    r"""A tariff cost group contains a set of tariff components.

    Parameters
    ----------
    tariff_cost_group_id : int
        The unique ID of the tariff cost group. The primary key of the table.

    tariff_id : int
        The unique ID of the tariff. The primary key of the table.
        Foreign key to :attr:`Tariff.tariff_id`. Is indexed.

    name : str
        The name of the tariff cost group. Must be unique within each `tariff_id`.

    description : str or None
        A description of the tariff cost group.

    updated_at : datetime.datetime or None
        The timestamp at which the tariff cost group was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the tariff cost group.

    created_at : datetime.datetime
        The timestamp at which the tariff cost group was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the tariff cost group.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'tariff_cost_group_id',
        'tariff_id',
        'name',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_tariff_cost_group'

    tariff_cost_group_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tariff_id: Mapped[int] = mapped_column(ForeignKey(Tariff.tariff_id, ondelete='CASCADE'))
    name: Mapped[str]
    description: Mapped[str | None]

    tariff: Mapped[Tariff] = relationship(back_populates='tariff_cost_groups')
    tariff_components: Mapped[list['TariffComponent']] = relationship(
        back_populates='tariff_cost_group'
    )
    tariff_cost_group_customer_group_links: Mapped[list['TariffCostGroupCustomerGroupLink']] = (
        relationship(back_populates='tariff_cost_group')
    )


Index(
    f'{TariffCostGroup.__tablename__}_tariff_id__name_uix',
    TariffCostGroup.tariff_id,
    TariffCostGroup.name,
    unique=True,
)


class TariffComponentType(ModifiedAndCreatedColumnMixin, Base):
    r"""The type of a tariff component.

    Parameters
    ----------
    tariff_component_type_id : int
        The unique ID of the tariff component type. The primary key of the table.

    name : str
        The name of the tariff component type. Must be unique. Is indexed.

    unit_id : str
        The unit of the tariff component type. Foreign key to :attr:`Unit.unit_id`.

    description : str or None
        A description of the tariff component type.

    updated_at : datetime.datetime or None
        The timestamp at which the tariff component type was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the tariff component type.

    created_at : datetime.datetime
        The timestamp at which the tariff component type was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the tariff component type.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'tariff_component_type_id',
        'name',
        'unit_id',
        'description',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_tariff_component_type'

    tariff_component_type_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    unit_id: Mapped[int] = mapped_column(ForeignKey(Unit.unit_id))
    description: Mapped[str | None]

    unit: Mapped[Unit] = relationship()
    tariff_components: Mapped[list['TariffComponent']] = relationship(
        back_populates='tariff_component_type'
    )


Index(
    f'{TariffComponentType.__tablename__}_name_uix',
    TariffComponentType.name,
    unique=True,
)


class TariffComponent(ModifiedAndCreatedColumnMixin, Base):
    r"""A tariff component with price information.

    Parameters
    ----------
    tariff_component_id : int
        The unique ID of the tariff component. The primary key of the table.

    tariff_component_type_id : int
        The type of tariff component. Must be unique for each `tariff_cost_group_id`.
        Foreign key to :attr:`TariffComponentType.tariff_component_type_id`. Is indexed.

    tariff_cost_group_id : int
        The tariff cost group that the component belongs to.
        Foreign key to :attr:`TariffCostGroup.tariff_cost_group_id`. Is indexed.

    price : int
        The price of the component in the smallest unit of the currency, e.g. cents or öre.

    price_outside_validity : int, default 0
        The price of the component outside of its validity range.

    validity_start : datetime or None
        The start date the tariff component is valid from (inclusive)
        in the configured business timezone of the app.

    validity_end : datetime or None
        The end date the tariff component is valid until (exclusive)
        in the configured business timezone of the app.

    updated_at : datetime.datetime or None
        The timestamp at which the tariff component was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the tariff component.

    created_at : datetime.datetime
        The timestamp at which the tariff component was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the tariff component.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'tariff_component_id',
        'tariff_component_type_id',
        'tariff_cost_group_id',
        'price',
        'price_outside_validity',
        'validity_start',
        'validity_end',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_tariff_component'

    tariff_component_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tariff_component_type_id: Mapped[int] = mapped_column(
        ForeignKey(TariffComponentType.tariff_component_type_id)
    )
    tariff_cost_group_id: Mapped[int] = mapped_column(
        ForeignKey(TariffCostGroup.tariff_cost_group_id, ondelete='CASCADE')
    )
    price: Mapped[int]
    price_outside_validity: Mapped[int] = mapped_column(server_default=text('0'))
    validity_start: Mapped[date | None] = mapped_column(
        Date,
        comment=(
            'The start date the tariff component is valid from (inclusive) '
            'in the configured business timezone of the app.'
        ),
    )
    validity_end: Mapped[date | None] = mapped_column(
        Date,
        comment=(
            'The end date the tariff component is valid until (exclusive) '
            'in the configured business timezone of the app.'
        ),
    )

    tariff_component_type: Mapped[TariffComponentType] = relationship(
        back_populates='tariff_components'
    )
    tariff_cost_group: Mapped[TariffCostGroup] = relationship(back_populates='tariff_components')


Index(
    f'{TariffComponent.__tablename__}_tariff_component_type_id_uix',
    TariffComponent.tariff_component_type_id,
    TariffComponent.tariff_cost_group_id,
    unique=True,
)

Index(
    f'{TariffComponent.__tablename__}_tariff_cost_group_id_ix', TariffComponent.tariff_cost_group_id
)


class TariffCostGroupCustomerGroupLink(ModifiedAndCreatedColumnMixin, Base):
    r"""The link between a tariff cost group and a customer group.

    Parameters
    ----------
    tariff_cost_group_id : int
        The ID of the tariff cost group. Part of the primary key.
        Foreign key to :attr:`TariffCostGroup.tariff_cost_group_id`.

    customer_group_id : int
        The ID of the customer group. Part of the primary key.
        Foreign key to :attr:`CustomerGroup.customer_group_id`.

    updated_at : datetime.datetime or None
        The timestamp at which the tariff cost group customer group link was last updated (UTC).

    updated_by : uuid.UUID or None
        The ID of the user that last updated the tariff cost group customer group link.

    created_at : datetime.datetime
        The timestamp at which the tariff cost group customer group link was created (UTC).
        Defaults to current timestamp.

    created_by : uuid.UUID or None
        The ID of the user that created the tariff cost group customer group link.
    """

    columns__repr__: ClassVar[tuple[str, ...]] = (
        'tariff_cost_group_id',
        'customer_group_id',
        'updated_at',
        'updated_by',
        'created_at',
        'created_by',
    )

    __tablename__ = 'ta_tariff_cost_group_customer_group_link'

    tariff_cost_group_id: Mapped[int] = mapped_column(
        ForeignKey(TariffCostGroup.tariff_cost_group_id), primary_key=True
    )
    customer_group_id: Mapped[int] = mapped_column(
        ForeignKey(CustomerGroup.customer_group_id), primary_key=True
    )

    tariff_cost_group: Mapped[TariffCostGroup] = relationship(
        back_populates='tariff_cost_group_customer_group_links'
    )
    customer_group: Mapped[CustomerGroup] = relationship(
        back_populates='tariff_cost_group_customer_group_links'
    )


Index(
    'ta_tcg_cg_link_cg_id__tcg_id_ix',
    TariffCostGroupCustomerGroupLink.customer_group_id,
    TariffCostGroupCustomerGroupLink.tariff_cost_group_id,
)
