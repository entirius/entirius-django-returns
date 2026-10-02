# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The access path: with django_access installed the X-API-KEY is an access token (``verify_api_key``, scope
``returns.api``). These keys are global: no channel pin.

Legacy keys reach it only through the import (``make_api_key``); the legacy table is never read on this path.
The keyed views also demand the customer JWT; the module's test settings have no ROOT_URLCONF, so views are
called directly.
"""

import json
import logging
import secrets
from datetime import timedelta
from unittest.mock import patch

import pytest

pytest.importorskip("django_access")

from django.contrib import admin  # noqa: E402
from django.core.management import CommandError, call_command  # noqa: E402
from django.test import RequestFactory  # noqa: E402
from django.utils import timezone  # noqa: E402
from django_access.models import ApiToken, Application  # noqa: E402
from django_access.services.access_service import Actor  # noqa: E402
from django_access.services.tokens import hash_key, issue_token, revoke_token, set_token_expiry  # noqa: E402

from django_returns.models import APIKey  # noqa: E402
from django_returns.utils.api_keys import API_SCOPE  # noqa: E402
from django_returns.views.order_return import create_return  # noqa: E402

OTHER_MODULE_SCOPES = ["reviews.moderate", "vault.api"]
PUBLISHABLE_SCOPE = "checkout.storefront"
API_KEY, ADMIN_KEY = "HTTP_X_API_KEY", "HTTP_X_API_ADMIN_KEY"
SYSTEM = Actor()


@pytest.fixture
def call(customer_jwt):
    """List returns with ``key`` in ``header``, as the customer unless ``with_jwt`` is off."""

    def call(key: str, header: str = API_KEY, channel_idx: str = "any-channel", with_jwt: bool = True):
        headers = {header: key}
        if with_jwt:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {customer_jwt}"
        return create_return(RequestFactory().get("/returns/", **headers), channel_idx=channel_idx, version="1")

    return call


def _body(response) -> tuple[int, object]:
    return response.status_code, json.loads(response.content)["data"]


def _passed(response) -> bool:
    return response.status_code == 200


def _refused(response) -> bool:
    return _body(response) == (401, "Invalid api key")


@pytest.fixture
def issue(db):
    """Issue an unpinned token of one scope; a secret scope gets the expiry it must carry."""
    application = Application.objects.create(name="returns-tests")

    def issue(scope: str = API_SCOPE) -> tuple[ApiToken, str]:
        expiry = timezone.now() + timedelta(days=30)
        return issue_token(application, scopes=[scope], channel_idx=None, expires_at=expiry, actor=SYSTEM)

    return issue


def _later(days: int):
    return patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(days=days))


@pytest.mark.django_db
class TestTokenLifecycle:
    def test_token_passes_and_records_its_use(self, issue, call):
        token, raw = issue()
        assert _passed(call(raw))
        token.refresh_from_db()
        assert token.last_used_at is not None

    def test_revoked_token_is_refused(self, issue, call):
        token, raw = issue()
        assert _passed(call(raw))
        revoke_token(token, actor=SYSTEM)
        assert _refused(call(raw))

    def test_expired_token_is_refused(self, issue, call):
        _, raw = issue()
        with _later(days=31):
            assert _refused(call(raw))

    def test_legacy_token_without_expiry_keeps_working(self, make_api_key, call):
        raw = make_api_key()
        token = ApiToken.objects.get(key_hash=hash_key(raw))
        assert (token.legacy, token.expires_at, token.scopes) == (True, None, [API_SCOPE])
        assert _passed(call(raw))
        with _later(days=3650):
            assert _passed(call(raw))

    def test_legacy_token_past_its_team_expiry_is_refused(self, make_api_key, call):
        raw = make_api_key()
        token = ApiToken.objects.get(key_hash=hash_key(raw))
        set_token_expiry(token, expires_at=timezone.now() + timedelta(days=1), actor=SYSTEM)
        assert _passed(call(raw))
        with _later(days=2):
            assert _refused(call(raw))

    def test_key_only_in_the_legacy_table_is_refused(self, call):
        raw = secrets.token_hex(32)
        APIKey.objects.create(key=raw)
        assert _refused(call(raw))


@pytest.mark.django_db
class TestScopeAndHeader:
    @pytest.mark.parametrize("scope", OTHER_MODULE_SCOPES)
    def test_token_of_another_module_is_refused(self, scope, issue, call):
        _, raw = issue(scope)
        assert _refused(call(raw))

    def test_publishable_token_is_refused(self, issue, call):
        _, raw = issue(PUBLISHABLE_SCOPE)
        assert _refused(call(raw))

    def test_token_in_x_api_admin_key_is_refused(self, issue, call):
        _, raw = issue()
        assert _refused(call(raw, header=ADMIN_KEY))

    def test_token_is_not_bound_to_a_channel(self, issue, call):
        _, raw = issue()
        assert _passed(call(raw, channel_idx="other-channel"))

    def test_token_without_customer_jwt_is_401(self, issue, call):
        _, raw = issue()
        assert _body(call(raw, with_jwt=False)) == (401, {})


@pytest.mark.django_db
def test_every_failure_gives_one_response(issue, call):
    expired, expired_raw = issue()
    ApiToken.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
    revoked, revoked_raw = issue()
    revoke_token(revoked, actor=SYSTEM)
    legacy_only = secrets.token_hex(32)
    APIKey.objects.create(key=legacy_only)
    keys = {
        "unknown": "ent_api_" + secrets.token_urlsafe(32),
        "expired": expired_raw,
        "revoked": revoked_raw,
        "other module": issue(OTHER_MODULE_SCOPES[0])[1],
        "publishable": issue(PUBLISHABLE_SCOPE)[1],
        "legacy table only": legacy_only,
    }
    responses = {kind: call(raw) for kind, raw in keys.items()}
    outcomes = {kind: (response.status_code, response.content) for kind, response in responses.items()}
    assert len(set(outcomes.values())) == 1, outcomes
    assert outcomes["unknown"][0] == 401


@pytest.mark.django_db
def test_presented_value_is_never_logged(issue, call, caplog):
    caplog.set_level(logging.DEBUG)
    _, raw = issue()
    unknown = "ent_api_" + secrets.token_urlsafe(32)
    assert _passed(call(raw))
    assert _refused(call(unknown))
    assert raw not in caplog.text
    assert unknown not in caplog.text


@pytest.mark.django_db
def test_key_admin_is_read_only(admin_user, rf):
    """The page itself (masked key, no key search) is pinned on both paths in ``test_key_admin.py``."""
    key = APIKey.objects.create()
    model_admin = admin.site.get_model_admin(APIKey)
    request = rf.get("/")
    request.user = admin_user
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request, key)
    assert not model_admin.has_delete_permission(request, key)


@pytest.mark.django_db
def test_key_command_refuses_and_names_the_token_command():
    with pytest.raises(CommandError, match=f"access_token create --scope {API_SCOPE}"):
        call_command("returns-generate-api-key")
    assert not APIKey.objects.exists()
