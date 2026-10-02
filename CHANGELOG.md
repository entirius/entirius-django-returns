# Changelog

## Unreleased

- Keys verified by django-access when installed: the X-API-KEY routes check access tokens through
  `verify_api_key` (scope `returns.api`, global — no channel pin), never the legacy table; the refusal stays
  401 "Invalid api key". Without django-access nothing changes. `returns-generate-api-key` then refuses and
  names `access_token create`; the key admin becomes read-only.
- The key admin shows only the last four characters of a key and no longer searches by key.
