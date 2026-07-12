# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django_utils.api.exceptions import BadRequest

if TYPE_CHECKING:
    pass


def paginate(params: dict, objs_list: QuerySet) -> tuple[dict, QuerySet]:
    """
    Paginates list or queryset according to request params

    Ex:
    qs = Model.objects.all()
    pagination, paginated_qs = paginate(request.GET, qs)
    """
    which_page = int(params.get("page", 1))
    objs_per_page = int(params.get("limit", 10))
    if objs_per_page > 100:
        raise BadRequest(message="Requesting more than 100 records per request is not allowed")
    else:
        paginator = Paginator(objs_list, objs_per_page)
        pages = paginator.num_pages
        records = paginator.count
        pagination_dict = {"page": which_page, "limit": objs_per_page, "pages": pages, "records": records}
        page = paginator.page(which_page)
        return pagination_dict, page.object_list
