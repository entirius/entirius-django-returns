# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import include, path

from django_returns import settings
from django_returns.views.order_return import (
    create_return,
    detail_return,
    download_attachment_view,
    download_return_file_view,
    get_return_candidate,
    get_return_extra_data,
)
from django_returns.views.return_attachment import get_order_attachment

api_paths = [
    path("orders/<str:order_id>/returns", get_return_candidate, name="create-return-for-order"),
    path("orders/<str:order_id>/returns_extra", get_return_extra_data, name="get-extra-return-for-order"),
    path("returns/", create_return, name="create-return-for-order"),
    path("returns/<str:return_id>", detail_return, name="modify-return-for-order"),
    path(
        "returns/<str:return_id>/file/<str:file_id>/customer/<str:uid>", get_order_attachment, name="order-attachment"
    ),
]

admin_paths = [
    path("attachments/order_return/<uuid:pk>", download_return_file_view, name="order-return-download"),
    path("attachments/order_attachment/<int:pk>", download_attachment_view, name="order-attachment-download"),
]

urlpatterns = [
    path(f"{settings.BASE_URL}/returns/<str:version>/<str:channel_idx>/", include(api_paths)),
    path(f"{settings.BASE_URL}/returns/", include(admin_paths)),
]
