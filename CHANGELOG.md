# Changelog

## Unreleased

- Access: the module declares its own access areas on its AppConfig and its admin views (copied from the
  entirius-django-access defaults; behaviour unchanged).
- Keys verified by django-access when installed: the X-API-KEY routes check access tokens through
  `verify_api_key` (scope `returns.api`, global — no channel pin), never the legacy table; the refusal stays
  401 "Invalid api key". Without django-access nothing changes. `returns-generate-api-key` then refuses and
  names `access_token create`; the key admin becomes read-only.
- The key admin dropped its `generate_new_key` action (it never had an implementation), on both paths.
- The key admin list shows only the last four characters of a key and no longer searches by key; the change page shows the raw key read-only without django-access and the masked one with it.
