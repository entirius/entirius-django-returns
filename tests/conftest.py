# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import secrets

import pytest


@pytest.fixture
def make_api_key(db):
    """Create an X-API-KEY the module accepts today and return its raw value.

    returns keys carry no channel and no scope, so both arguments are accepted and ignored. The key contract tests
    go through this helper only, so moving the check onto another key store changes this function, never the
    assertions. Values are random and never printed.
    """
    from django_returns.models import APIKey

    def make_api_key(channel=None, scope: str | None = None) -> str:
        raw = secrets.token_hex(32)
        APIKey.objects.create(key=raw)
        return raw

    return make_api_key
