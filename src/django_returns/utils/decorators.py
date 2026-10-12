# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import wraps

from django_utils.api.decorators import api_view
from django_utils.api.exceptions import Unauthorized

from django_returns.utils.api_keys import key_is_valid


def authorize_api(view):
    @wraps(view)
    @api_view
    def _wrapped(request, *args, **kwargs):
        passed = key_is_valid(request, channel_idx=kwargs.get("channel_idx"))
        if passed:
            response = view(request, *args, **kwargs)
            return response
        else:
            raise Unauthorized("Invalid api key")

    return _wrapped
