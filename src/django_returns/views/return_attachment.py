# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_utils.api.decorators import api_view, require_http_method
from django_utils.api.exceptions import Forbidden, NotFound
from process_logger.process_logger import ProcessLogger

from django_returns.models import Channel, OrderReturn, ReturnAttachment

logger_process = logging.getLogger("process")


@csrf_exempt
@api_view
@require_http_method("GET")
def get_order_attachment(request, channel_idx=None, return_id=None, file_id=None, uid=None, *args, **kwargs):
    logger = ProcessLogger("DJANGO_RETURNS_API_RETURN")
    try:
        order_return = OrderReturn.objects.get(id=return_id)
        channel = Channel.objects.get(idx=channel_idx)
    except OrderReturn.DoesNotExist:
        logger.set_code(4002)
        logger.error("Customer does not have order with this UUID.")
        raise NotFound("4002")
    except Channel.DoesNotExist:
        logger.set_code(4003)
        logger.error(f"Channel {channel_idx} does not exist.")
        raise NotFound("4003")

    if str(order_return.order.customer.uid) != str(uid):
        logger.set_code(4002)
        logger.error("Customer does not have order with this UUID.")
        raise Forbidden(message=4002, status="return_and_user_unmatched")

    try:
        file = ReturnAttachment.objects.get(order_return=order_return, pk=file_id)
    except ObjectDoesNotExist as e:
        logger.exception(e)
        logger.set_code(4011)
        raise NotFound(message=str(e), status="file_doesnt_exists")

    file_path = file.attachment.path
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response["Content-Disposition"] = "attachment; filename=" + os.path.basename(file_path)
            response["x-filename"] = file.name
            response["Access-Control-Expose-Headers"] = "x-filename"
            return response
    raise NotFound(message="File does't exists", status="file_doesnt_exists")
