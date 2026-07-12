# AGENTS.md

Order returns (RMA) for the Volkanos checkout — distribution `entirius-django-returns`,
Django app `django_returns`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_returns` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.

## Architecture

```
src/django_returns/
├── apps.py                 # AppConfig (is_volkanos=True)
├── settings.py             # host-overridable settings; PRIVATE_DIR required (fail-fast)
├── models/                 # APIKey, Channel, OrderReturn, ReturnAttachment (+BaseModel)
├── domain/dto/             # marshmallow-dataclass DTO for order returns
├── views/                  # storefront API (order_return, return_attachment) — X-API-KEY guarded
├── worker/order_return.py  # status flow + confirmation e-mail (django_email)
├── utils/                  # api decorators (django_utils), pagination
├── admin.py                # ModelAdmin registrations (inline paginator)
├── bi.py                   # BI events (bievents)
├── urls.py                 # mounts return API under API_BASE_URL
└── management/commands/    # returns-generate-api-key
```

## Dependencies

| Module | Purpose |
|---|---|
| `django_checkout` | Order / ProductRepresentation (FK + enums, order status flow) |
| `django_email` | return confirmation e-mail service (hard import in worker) |
| `django_utils` | api decorators, exceptions, BaseModel |
| `django_accounts` | schema-only FK `OrderReturn.customer` (no Python import) |
| `pdf_generator` | return form PDF (views) |
| `bievents`, `process_logger` | BI events + logging |
| `django-admin-inline-paginator` | admin inlines |

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `PRIVATE_DIR` | _none_ — REQUIRED | attachment storage root (`returns/` subdir) |
| `API_BASE_URL` | `"api"` | URL prefix |
| `NEW_ACCOUNT_EMAIL_TEMPLATE_PATH_HTML` | module template | e-mail template override |
| `LOGO_URL` | `""` | logo used in e-mail templates |

## Testing

```bash
# Postgres required; tests/settings.py reads DATABASE_URL
# (default postgresql://postgres:postgres@localhost:5432/test).
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test make test
```

Test suite is an import smoke test (`tests/test_smoke.py`) — real RMA flow tests are an open TODO.

## References

- `docs/return_api.md` — endpoint reference (Polish; translation pending).
