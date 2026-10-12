# entirius-django-returns

A Django module for order returns (RMA) in Entirius, the open-source modular ecommerce platform. Customers file a
return request for a completed order, attach files and download a PDF return form; the order moves to its returned
status.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-returns.svg)](https://pypi.org/project/entirius-django-returns/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-returns.svg)](https://pypi.org/project/entirius-django-returns/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-returns/blob/develop/LICENSE)

## What it does

- Lists the items of a completed order that can still be returned, within a configurable return window.
- Creates return requests with the return method, the chosen solution, a comment and attachments.
- Generates a PDF return form and sends a confirmation email.
- Links every return to the checkout order and to the customer account.
- Exposes a key-protected storefront REST API per sales channel, plus admin download routes for attachments.

## Installation

```shell
uv add entirius-django-returns
pip install entirius-django-returns
```

```python
INSTALLED_APPS = [
    ...
    "django_utils",
    "django_regional",
    "django_accounts",
    "django_pim",
    "django_pricemanager",
    "django_email",
    "django_checkout",
    "django_returns",
]

# urls.py
urlpatterns = [
    path("", include("django_returns.urls")),
]
```

Required setting: `PRIVATE_DIR`, the root directory of attachment storage; the module refuses to import without it.
The checkout module it builds on has required settings of its own, listed in
https://github.com/entirius/entirius-django-checkout/blob/develop/README.md.
Optional settings (`API_BASE_URL`, `DAYS_TO_RETURN`, `LOGO_URL`, `PDF_RETURN_TEMPLATE`) are listed in
https://github.com/entirius/entirius-django-returns/blob/develop/AGENTS.md (section Settings).

The storefront API reads its key from the `X-API-KEY` header. With `django_access` installed the key is an access
token with the scope `returns.api`:

```shell
python manage.py access_token create --application <name> --create-application --scope returns.api --channel <idx>
```

Without `django_access`, create the key with `python manage.py returns-generate-api-key`.

## Quick start

```python
from django_returns.models import OrderReturn, ReturnStatus

open_returns = OrderReturn.objects.filter(status=ReturnStatus.OPEN).select_related("order", "customer")
```

## Requirements

- Python 3.11 or newer, Django 5.0 or newer.
- PostgreSQL.
- Entirius packages pulled in: `entirius-django-checkout` (orders and their status flow), `entirius-django-email`
  (confirmation email), `entirius-django-accounts` (customer), `entirius-django-utils`, `entirius-py-pdf-generator`
  (return form), `entirius-py-bievents`, `entirius-py-process-logger`.

## Documentation

- Module docs: https://github.com/entirius/entirius-django-returns/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-returns/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos) as a satellite of the checkout module.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-checkout,
  https://github.com/entirius/entirius-django-accounts, https://github.com/entirius/entirius-django-email

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-returns/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-returns/blob/develop/LICENSE.
