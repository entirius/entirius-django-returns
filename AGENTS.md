# AGENTS.md

Order returns (RMA) for the Entirius checkout — distribution `entirius-django-returns`,
Django app `django_returns`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |
| `make test-legacy` | test suite without django_access (legacy key path) |

Tests need PostgreSQL: set `DATABASE_URL` (the default in `tests/settings.py` points at a local postgres).

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_returns` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Access: areas and token scopes live on the AppConfig (`access_areas`, `access_token_scopes`,
  `access_route_rules`), every admin view carries `access_area`; a new admin route without one fails
  `tests/test_access_ownership.py`.
- Default: do not commit — git is the user's call.
- No AI attribution in commits or PR descriptions.

## Architecture

```
src/django_returns/
├── apps.py                 # AppConfig (is_volkanos=True)
├── settings.py             # host-overridable settings; PRIVATE_DIR required (fail-fast)
├── models/                 # APIKey, Channel, OrderReturn, ReturnAttachment (+BaseModel)
├── domain/dto/             # marshmallow-dataclass DTO for order returns
├── views/                  # storefront API (order_return, return_attachment) — X-API-KEY guarded
├── worker/order_return.py  # status flow + confirmation e-mail (django_email)
├── utils/                  # api decorators (django_utils), pagination; api_keys.py: the key check — django_access token
│                           # (returns.api) when installed, else APIKey
├── admin.py                # ModelAdmin registrations (inline paginator)
├── bi.py                   # BI events (bievents)
├── urls.py                 # mounts return API under API_BASE_URL
└── management/commands/    # returns-generate-api-key (refuses when django_access is installed)
```

Module dependencies: `django_checkout` (Order / ProductRepresentation FKs, enums, order status flow), `django_email`
(confirmation e-mail, hard import in the worker), `django_utils` (api decorators, exceptions, BaseModel),
`django_accounts` (schema-only FK `OrderReturn.customer`, no Python import), `pdf_generator` (return form PDF, views),
`bievents` and `process_logger` (BI events + logging), `django-admin-inline-paginator` (admin inlines).

The test suite is an import smoke test (`tests/test_smoke.py`) — real RMA flow tests are an open TODO.

| Topic | Where |
|---|---|
| Endpoint reference (Polish; translation pending) | `docs/return_api.md` |
| Settings and the PDF form template | `src/django_returns/settings.py` |
| Key check (access token or legacy key) | `src/django_returns/utils/api_keys.py` |

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `PRIVATE_DIR` | _none_ — REQUIRED | attachment storage root (`returns/` subdir) |
| `API_BASE_URL` | `"api"` | URL prefix |
| `NEW_ACCOUNT_EMAIL_TEMPLATE_PATH_HTML` | module template | e-mail template override |
| `LOGO_URL` | `""` | logo used in e-mail templates |
| `DAYS_TO_RETURN` | `14` | return window after the order was completed |
| `PDF_RETURN_TEMPLATE` | module template | layout of the PDF return form |
