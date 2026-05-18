![Tests](https://github.com/volfpeter/motorhead/actions/workflows/tests.yml/badge.svg)
![Linters](https://github.com/volfpeter/motorhead/actions/workflows/linters.yml/badge.svg)
![Documentation](https://github.com/volfpeter/motorhead/actions/workflows/build-docs.yml/badge.svg)
![PyPI package](https://img.shields.io/pypi/v/motorhead?color=%2334D058&label=PyPI%20Package)

**Source code**: [https://github.com/volfpeter/motorhead](https://github.com/volfpeter/motorhead)

**Documentation and examples**: [https://volfpeter.github.io/motorhead](https://volfpeter.github.io/motorhead/)

# Motorhead

Async MongoDB/DocumentDB with vanilla Pydantic v2+ - made easy.

Key features:

- Database **model** and API design with vanilla `Pydantic` v2+.
- Relationship support and validation using async **validators and delete rules** with a declarative, decorator-based syntax.
- ODM-like **query builder** for convenient, typed, and Pythonic query construction.
- Declarative **index** specification.
- Typed **utilities** for convenient model and API creation.
- Ready to use, customizable **async service layer** with **transaction support** that integrates all the above to keep your business logic clean, flexible, and easy to understand.
- **Simplicity**: by not being a classic ODM, the codebase is very simple and easy to understand (even contribute to) even for relative beginners.

By providing a convenient, declarative middle layer between MongoDB/DocumentDB and your API, `motorhead` is halfway between an object document mapper (based on vanilla `Pydantic`) and a database driver (by wrapping the official async `pymongo` driver). What's missing is the built-in ODM performance and memory overhead, whose benefits are rarely felt when working with document databases.

## Installation

The library is available on PyPI and can be installed with:

```console
$ pip install motorhead
```

## Examples

See the [documentation](https://volfpeter.github.io/motorhead/fastapi-example/) for usage and application examples.

## Requirements

The project depends on `pymongo` (the official async MongoDB driver) and `pydantic` v2+.

## Development

Use `black` for code formatting, `mypy` for static code analysis, `ruff` for linting, and `pytest` (with `pytest-asyncio` and `pytest-docker`) for testing.

The documentation is built with `mkdocs-material` and `mkdocstrings`.

## Contributing

All contributions are welcome.

## License - MIT

The library is open-sourced under the conditions of the [MIT license](https://choosealicense.com/licenses/mit/).
