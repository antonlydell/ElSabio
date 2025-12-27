# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]


## [0.3.0] - 2025-12-27

Import data to the Tariff Analyzer module!

The new `elsabio` CLI is used to manage the ElSabio application. It provides capabilities to import
the data needed by the Tariff Analyzer module. This includes *products*, *facilities*, *facility contracts*
and *meter data*. This functionality is exposed under the subcommand `ta` (Tariff Analyzer). The data is
imported from parquet files and the configuration has been extended with a `tariff_analyzer` section in
which the data import paths are defined.


### Added

- `elsabio` : The CLI to manage the ElSabio application.

- `DuckDB` : DuckDB has been added as a dependency and is used as the query engine for analytical processes.


## [0.2.0] - 2025-11-29

Initialize the database and sign in!

Added the `init` page, which initializes the database of **ElSabio** and enables creating users that should
be able to register and sign in. The `init` page can be launched through the new CLI `elsabio-web`, which
is used to launch the ElSabio web application or serve individual pages from the app. Users can then register
a passkey and sign in to the application through the new `sign-in` page. Added support to load the application's
configuration and setup logging.


### Added

- `elsabio-web` : The CLI to launch the ElSabio web application or serve individual pages from the app.


## [0.1.0] - 2025-09-20

A first release and declaration of the project.


### Added

- The initial structure of the project.

- Registration on [PyPI](https://pypi.org/project/ElSabio/0.1.0/).


[Unreleased]: https://github.com/antonlydell/ElSabio/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/antonlydell/ElSabio/releases/tag/v0.3.0
[0.2.0]: https://github.com/antonlydell/ElSabio/releases/tag/v0.2.0
[0.1.0]: https://github.com/antonlydell/ElSabio/releases/tag/v0.1.0
