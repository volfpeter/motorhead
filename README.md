# Motorhead

Async MongoDB with Pydantic v2+ - made easy.

Key features:

- Database **model** and API design with `Pydantic` v2+.
- Relationship support and validation using async **validators and delete rules** with a declarative, decorator-based syntax.
- Declarative **index** specification.
- Typed **utilities** for convenient model and API creation.
- Ready to use, customizable **async service layer** with **transaction support** that integrates all the above to keep your API and business logic clean, flexible, and easy to understand.

By providing a convenient, declarative middle layer between MongoDB and your API, `motorhead` is halfway between an object document mapper (based on `Pydantic`) and a database driver (by wrapping the official, async `motor` driver). What's missing is the built-in ODM performance and memory overhead, whose benefits are rarely felt when working with document databases.

See the [full documentation here](https://volfpeter.github.io/motorhead/).

## Installation

The library is available on PyPI and can be installed with:

```console
$ pip install motorhead
```

## Examples

See the [documentation](https://volfpeter.github.io/motorhead/fastapi-example/) for usage and application examples.

## Requirements

The project depends on `motor` (the official asyncio MongoDB driver, which is built on top of `pymongo` and `bson`) and `pydantic` v2+.

## Development

Use `black` for code formatting, `mypy` for static code analysis, and `ruff` for linting.

The documentation is built with `mkdocs-material` and `mkdocstrings`.

## Contributing

All contributions are welcome.

## Notes

This project is the continuation of [fastapi-motor-oil](https://github.com/volfpeter/fastapi-motor-oil) with support for [Pydantic v2](https://docs.pydantic.dev/latest/migration/), among some other, minor improvements. Migration from `fastapi-motor-oil` should be easy, but if you need help, just create an issue in the issue tracker.

## License - MIT

The library is open-sourced under the conditions of the [MIT license](https://choosealicense.com/licenses/mit/).
