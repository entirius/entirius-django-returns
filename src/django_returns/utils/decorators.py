# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import wraps

from django_utils.api.decorators import api_view
from django_utils.api.exceptions import Unauthorized

from django_returns.models import APIKey


def authorize_api(view):
    def is_allowed(request):
        key = request.headers.get("X-API-KEY")
        query = APIKey.objects.filter(key=key)
        return query.exists()

    @wraps(view)
    @api_view
    def _wrapped(request, *args, **kwargs):
        passed = is_allowed(request)
        if passed:
            response = view(request, *args, **kwargs)
            return response
        else:
            raise Unauthorized("Invalid api key")

    return _wrapped
