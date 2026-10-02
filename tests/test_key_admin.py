# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The key admin on either path (with or without django_access): only the last four characters, no key search."""

import pytest
from django.contrib import admin

from django_returns.models import APIKey


@pytest.mark.django_db
def test_key_admin_never_shows_the_raw_key(admin_user, rf, settings):
    settings.ROOT_URLCONF = "tests.admin_urls"
    key = APIKey.objects.create()
    model_admin = admin.site.get_model_admin(APIKey)
    request = rf.get("/")
    request.user = admin_user
    assert "key" not in model_admin.search_fields
    for response in (model_admin.changelist_view(request), model_admin.change_view(request, str(key.pk))):
        html = response.render().content.decode()
        assert response.status_code == 200
        assert key.key not in html
        assert f"…{key.key[-4:]}" in html
