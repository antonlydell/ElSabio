# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The Tariff Analyzer config models."""

# Standard library
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

# Third party
from pydantic import Field, ValidationInfo, field_validator

# Local
from elsabio.config.core import HOME_DIR, BaseConfigModel, ImportMethod, PluginConfig
from elsabio.datetime import parse_date_range_expression
from elsabio.exceptions import ElSabioError

TARIFF_ANALYZER_DIR = HOME_DIR / 'tariff_analyzer'
DEFAULT_DATA_DIR = TARIFF_ANALYZER_DIR / 'data'
DEFAULT_METER_DATA_DIR = DEFAULT_DATA_DIR / 'meter_data'

DEFAULT_TARIFF_VALUE_DIR = DEFAULT_DATA_DIR / 'tariff_value'
DEFAULT_TARIFF_VALUE_FACILITY_DIR = DEFAULT_TARIFF_VALUE_DIR / 'facility'
DEFAULT_TARIFF_VALUE_TOTAL_DIR = DEFAULT_TARIFF_VALUE_DIR / 'total'

DEFAULT_ERROR_DIR = DEFAULT_DATA_DIR / 'error'
DEFAULT_ERROR_DIR_TARIFF_VALUE = DEFAULT_ERROR_DIR / 'tariff_value'
DEFAULT_ERROR_DIR_MAP_FACILITIES = DEFAULT_ERROR_DIR / 'map_facilities'
DEFAULT_ERROR_DIR_IMPORT = DEFAULT_ERROR_DIR / 'import'


class DataSource(StrEnum):
    r"""The available data sources of the Tariff Analyzer module."""

    PRODUCT = 'product'
    FACILITY = 'facility'
    FACILITY_CONTRACT = 'facility_contract'
    ACTIVE_ENERGY_CONS = 'active_energy_cons'
    ACTIVE_ENERGY_PROD = 'active_energy_prod'
    MAX_ACTIVE_POWER_CONS = 'max_active_power_cons'
    MAX_ACTIVE_POWER_PROD = 'max_active_power_prod'
    MAX_REACTIVE_POWER_CONS = 'max_reactive_power_cons'
    MAX_REACTIVE_POWER_PROD = 'max_reactive_power_prod'
    MAX_DEB_ACTIVE_POWER_CONS_HIGH_LOAD = 'max_deb_active_power_cons_high_load'
    MAX_DEB_ACTIVE_POWER_CONS_LOW_LOAD = 'max_deb_active_power_cons_low_load'


class DataSourceConfig(BaseConfigModel):
    r"""The configuration of an importable data source.

    Parameters
    ----------
    method : elsabio.config.ImportMethod
        The method for importing the data needed by Tariff Analyzer.

    path : pathlib.Path
        The path to the directory where data files to import are located if
        `method` is :attr:ImportMethod.FILE`, or the directory where the input
        data is temporarily saved before import if `method` is :attr:ImportMethod.PLUGIN`.

    interval : tuple[date, date | None] | None, default None
        The interval in which to import data if `method` is :attr:ImportMethod.PLUGIN`.

    plugin : elsabio.config.PluginConfig or None, default None
        The configuration of the plugin to use for importing data if `method` is
        :attr:ImportMethod.PLUGIN`.
    """

    method: ImportMethod
    path: Path
    interval: tuple[date, date | None] | None = None
    plugin: PluginConfig | None = Field(default=None, validate_default=True)

    @field_validator('path')
    @classmethod
    def validate_path(cls, path: Path) -> Path | None:
        r"""Validate the `path` attribute."""

        path = path.expanduser().resolve()

        if not path.exists():
            raise ValueError(f'The import path = "{path}" does not exist!')

        if not path.is_dir():
            raise ValueError(f'The import path = "{path}" is not a directory!')

        return path

    @field_validator('interval', mode='before')
    @classmethod
    def validate_interval(cls, interval: Any) -> tuple[date, date | None] | None:
        r"""Validate the plugin configuration."""

        if interval is None:
            return interval

        if isinstance(interval, str):
            try:
                start, end = parse_date_range_expression(expr=interval)
            except ElSabioError as e:
                raise ValueError(str(e)) from None

            return start.date(), end if end is None else end.date()

        raise ValueError(f'Invalid interval "{interval}"!')

    @field_validator('plugin')
    @classmethod
    def validate_plugin(cls, v: PluginConfig | None, info: ValidationInfo) -> PluginConfig | None:
        r"""Validate the plugin configuration."""

        method = info.data.get('method')

        if v is None:
            if method == ImportMethod.PLUGIN:
                raise ValueError(f'No plugin configuration found and method = "{method}"!')
        elif info.data.get('interval') is None:
            raise ValueError(f'No interval specified and method = "{method}"!')

        return v


class TariffAnalyzerConfig(BaseConfigModel):
    r"""The configuration of the Tariff Analyzer module.

    Parameters
    ----------
    enabled : bool, default True
        True if the Tariff Analyzer module is enabled and False otherwise.

    data_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data'
        The path to the data directory of the Tariff Analyzer module
        where the imported and calculated data will reside.

    meter_data_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data/meter_data'
        The path to the meter data directory where the imported meter data will reside.
        If not specified the sub-directory "meter_data" in `data_dir` is used.

    tariff_value_facility_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data/tariff_value/facility'
        The path to the directory where the calculated tariff values per facility
        and tariff component are stored. If not specified the sub-directory
        "tariff_value/facility" in `data_dir` is used.

    tariff_value_total_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data/tariff_value/total'
        The path to the directory where the calculated total tariff values per tariff
        component are stored. If not specified the sub-directory "tariff_value/total"
        in `data_dir` is used.

    tariff_value_error_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data/error/tariff_value'
        The path to the directory where to write the error results from the validation
        of the tariff calculations.

    map_facilities_error_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data/error/map_facilities'
        The path to the directory where to write the error results from the validation
        of the facility customer group mapping operation.

    import_error_dir : pathlib.Path, default '~/.elsabio/tariff_analyzer/data/error/import'
        The path to the directory where to write the error results from the validation
        of the data import.

    error_file_col_sep : str, default ';'
        The column separator to use for the csv files of validation error results.

    error_file_encoding : str, default 'utf-8'
        The character encoding of the csv files with validation error results.

    data : dict[elsabio.config.tariff_analyzer.DataSource, elsabio.config.tariff_analyzer.DataSourceConfig], default {}
        The data sources needed by Tariff Analyzer.
    """

    enabled: bool = True

    data_dir: Path = DEFAULT_DATA_DIR
    meter_data_dir: Path = Field(default=None, validate_default=True)
    tariff_value_facility_dir: Path = Field(default=None, validate_default=True)
    tariff_value_total_dir: Path = Field(default=None, validate_default=True)

    tariff_value_error_dir: Path = Field(default=None, validate_default=True)
    map_facilities_error_dir: Path = Field(default=None, validate_default=True)
    import_error_dir: Path = Field(default=None, validate_default=True)
    error_file_col_sep: str = ';'
    error_file_encoding: str = 'utf-8'

    data: dict[DataSource, DataSourceConfig] = Field(default={})

    @field_validator('data_dir')
    @classmethod
    def validate_data_dir(cls, path: Path) -> Path:
        r"""Validate the `data_dir` field."""

        path = path.expanduser().resolve()

        if not path.exists():
            raise ValueError(f'The tariff_analyzer.data_dir = "{path}" does not exist!')

        if not path.is_dir():
            raise ValueError(f'tariff_analyzer.data_dir = "{path}" must be a directory!')

        return path

    @field_validator(
        'meter_data_dir',
        'tariff_value_facility_dir',
        'tariff_value_total_dir',
        'tariff_value_error_dir',
        'map_facilities_error_dir',
        'import_error_dir',
        mode='before',
    )
    @classmethod
    def validate_sub_dirs(cls, value: Any, info: ValidationInfo) -> Path:
        r"""Validate the sub-directory fields based on the value of `data_dir`."""

        if (data_dir := info.data.get('data_dir')) is None:
            raise ValueError('tariff_analyzer.data_dir is missing!')

        if (field_name := info.field_name) is None:
            raise ValueError(f'{field_name} is missing for tariff_analyzer!')

        default_paths = {
            'meter_data_dir': data_dir / 'meter_data',
            'tariff_value_facility_dir': data_dir / 'tariff_value' / 'facility',
            'tariff_value_total_dir': data_dir / 'tariff_value' / 'total',
            'tariff_value_error_dir': data_dir / 'error' / 'tariff_value',
            'map_facilities_error_dir': data_dir / 'error' / 'map_facilities',
            'import_error_dir': data_dir / 'error' / 'import',
        }

        if isinstance(value, Path):
            path: Path | None = value
        elif isinstance(value, str):
            path = Path(value)
        else:
            path = default_paths.get(field_name)

        if path is None:
            raise ValueError(f'Missing default path for tariff_analyzer.{field_name}!')

        path = path.expanduser().resolve()

        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                raise ValueError(
                    f'Insufficient permissions to create directory tariff_analyzer.{field_name} = '
                    f'"{path}"!\n{e!s}'
                ) from None

        if not path.is_dir():
            raise ValueError(f'tariff_analyzer.{field_name} = "{path}" must be a directory!')

        return path
