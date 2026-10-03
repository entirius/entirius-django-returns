# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The one key check of the keyed routes (X-API-KEY).

With ``django_access`` installed a key is an access token checked by ``verify_api_key`` for ``API_SCOPE``; the keys
are global (no channel pin), and the legacy table is never read on that path — legacy keys live on as imported tokens
(D28). Without the module: today's legacy query, unchanged. The presented value is never logged.
"""

from types import SimpleNamespace

from django.apps import apps
from django.http import HttpRequest

from django_returns.models import APIKey

API_SCOPE = "returns.api"
_HEADER = "HTTP_X_API_KEY"


def access_installed() -> bool:
    return apps.is_installed("django_access")


def mask_key(key: str) -> str:
    """What an admin page shows of a key: its last four characters."""
    return f"…{key[-4:]}"


def token_command() -> str:
    """What replaces the legacy key command when access is installed."""
    return f"manage.py access_token create --scope {API_SCOPE} --application <name> --expires-days <days>"


def key_is_valid(request: HttpRequest) -> bool:
    """True when X-API-KEY carries a key for ``API_SCOPE``."""
    key = request.META.get(_HEADER)
    if not key:
        return False
    if access_installed():
        return _token_is_valid(request, key)
    return APIKey.objects.filter(key=key).exists()


def _token_is_valid(request: HttpRequest, key: str) -> bool:
    """``verify_api_key`` sees only X-API-KEY: the X-API-ADMIN-KEY alias never stands in for it."""
    from django_access.services.tokens import verify_api_key

    token = verify_api_key(SimpleNamespace(META={_HEADER: key}), API_SCOPE, None)
    if token is not None:
        request.access_token = token
    return token is not None
