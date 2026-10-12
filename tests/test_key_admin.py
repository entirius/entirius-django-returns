# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The key admin on either path: the list masks keys, no key search; the change page masks them only with access."""

from unittest.mock import patch

import pytest
from django.contrib import admin

from django_returns.models import APIKey


def _pages(admin_user, rf, settings, access: bool) -> tuple[APIKey, str, str]:
    settings.ROOT_URLCONF = "tests.admin_urls"
    key = APIKey.objects.create()
    model_admin = admin.site.get_model_admin(APIKey)
    request = rf.get("/")
    request.user = admin_user
    assert not model_admin.get_search_fields(request)
    with patch("django_returns.admin.access_installed", return_value=access):
        changelist = model_admin.changelist_view(request)
        change = model_admin.change_view(request, str(key.pk))
    assert changelist.status_code == change.status_code == 200
    return key, changelist.render().content.decode(), change.render().content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("access", [True, False])
def test_key_list_masks_the_key(admin_user, rf, settings, access):
    key, changelist, _ = _pages(admin_user, rf, settings, access)
    assert key.key not in changelist
    assert f"…{key.key[-4:]}" in changelist


@pytest.mark.django_db
def test_change_page_masks_the_key_with_access(admin_user, rf, settings):
    key, _, change = _pages(admin_user, rf, settings, access=True)
    assert key.key not in change
    assert f"…{key.key[-4:]}" in change


@pytest.mark.django_db
def test_change_page_shows_the_raw_key_read_only_without_access(admin_user, rf, settings):
    key, _, change = _pages(admin_user, rf, settings, access=False)
    assert key.key in change
    assert 'name="key"' not in change
