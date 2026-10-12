# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The legacy key path (no django_access): the generator command works and the key admin keeps its permissions.

Runs only with ``make test-legacy`` (``ENTIRIUS_TEST_NO_ACCESS=1``) or where django-access is not importable.
"""

import os
from importlib.util import find_spec

import pytest
from django.contrib import admin
from django.core.management import call_command

from django_returns.models import APIKey

pytestmark = pytest.mark.skipif(
    not os.environ.get("ENTIRIUS_TEST_NO_ACCESS") and find_spec("django_access") is not None,
    reason="legacy path only",
)


@pytest.mark.django_db
def test_key_command_creates_and_writes_a_key(tmp_path):
    target = tmp_path / "key"
    call_command("returns-generate-api-key", file_path=str(target))
    key = APIKey.objects.get()
    assert target.read_text() == key.key


@pytest.mark.django_db
def test_key_admin_keeps_add_change_delete(admin_user, rf):
    key = APIKey.objects.create()
    model_admin = admin.site.get_model_admin(APIKey)
    request = rf.get("/")
    request.user = admin_user
    assert model_admin.has_add_permission(request)
    assert model_admin.has_change_permission(request, key)
    assert model_admin.has_delete_permission(request, key)
