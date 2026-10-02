# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Characterization of today's returns key contract (X-API-KEY + customer JWT).

Keyed views stack ``@authenticate @authorize_api @require_authentication``: the key is checked before the
customer, and keys carry no channel. Pins what they answer — quirks included — so moving the key check onto
another key store cannot change a status or a body. Keys come only from the ``make_api_key`` helper.

The module has no ROOT_URLCONF in its test settings, so views are called directly.
"""

import json
import secrets
import uuid

import pytest
from django.test import RequestFactory

from django_returns.views.order_return import create_return
from django_returns.views.return_attachment import get_order_attachment

factory = RequestFactory()


def _list_returns(key: str | None, jwt: str | None = None, channel_idx: str = "any-channel"):
    headers = {}
    if key is not None:
        headers["HTTP_X_API_KEY"] = key
    if jwt is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {jwt}"
    return create_return(factory.get("/returns/", **headers), channel_idx=channel_idx, version="1")


def _refusal(response) -> tuple[int, str, object]:
    body = json.loads(response.content)
    return response.status_code, body["meta"]["status"], body["data"]


@pytest.fixture(autouse=True)
def _live_key(make_api_key):
    """Valid keys exist in every test, so a refusal proves the lookup, not an empty key store."""
    make_api_key()


@pytest.mark.django_db
class TestAuthorizeApi:
    def test_no_key_and_no_jwt_is_401(self):
        assert _refusal(_list_returns(None)) == (401, "UNAUTHORIZED", "Invalid api key")

    def test_wrong_key_with_customer_jwt_is_401(self, customer_jwt):
        wrong_key = secrets.token_hex(32)
        response = _list_returns(wrong_key, jwt=customer_jwt)
        assert _refusal(response) == (401, "UNAUTHORIZED", "Invalid api key")
        assert wrong_key not in response.content.decode()

    def test_right_key_without_customer_jwt_is_401(self, make_api_key):
        assert _refusal(_list_returns(make_api_key())) == (401, "UNAUTHORIZED", {})

    def test_right_key_with_customer_jwt_lists_returns(self, customer_jwt, make_api_key):
        response = _list_returns(make_api_key(), jwt=customer_jwt)
        assert response.status_code == 200
        assert json.loads(response.content)["data"] == []

    def test_key_is_not_bound_to_a_channel(self, customer_jwt, make_api_key):
        assert _list_returns(make_api_key(), jwt=customer_jwt, channel_idx="other-channel").status_code == 200


@pytest.mark.django_db
def test_return_attachment_answers_without_a_key():
    request = factory.get("/")
    response = get_order_attachment(
        request, channel_idx="any-channel", return_id=str(uuid.uuid4()), file_id="1", uid=str(uuid.uuid4())
    )
    assert response.status_code == 404
