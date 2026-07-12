# entirius-django-returns

Order returns (RMA) for the Volkanos checkout: customer return requests with attachments,
return PDF forms and status flow. Extends `django_checkout` (orders) and links returns
to `django_accounts` customers.

## Installation

```shell
pip install entirius-django-returns
```

## Configuration

`PRIVATE_DIR` is required by the host service (attachment storage; fail-fast at import).
Optional: e-mail template paths and `LOGO_URL` — see `src/django_returns/settings.py`.

## Development

```shell
make install   # uv sync (incl. extras)
make test      # run tests
make check     # ruff lint + format-check
```

## API

See `docs/return_api.md` for the endpoint reference.

## License

MPL-2.0
