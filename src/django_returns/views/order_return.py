# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import subprocess
import tempfile
from dataclasses import asdict
from datetime import datetime
from functools import reduce

from django.core.files import File
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import FileResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django_utils.api.decorators import (
    api_view,
    authenticate,
    parse_body,
    parse_parameters,
    require_authentication,
    require_http_method,
)
from django_utils.api.exceptions import BadRequest, NotFound
from django_utils.api.responses import PaginatedResponse, Response
from pdf_generator.worker.latex import PDFGenerator
from process_logger import ProcessLogger

from django_returns import settings
from django_returns.domain.dto.order_return import (
    GetReturnParams,
    OrderReturnListing,
    ReturnCreateRequest,
    ReturnListing,
    ReturnParams,
    ReturnResponse,
    ReturnResponseExtra,
)
from django_returns.models import (
    Channel,
    OrderReturn,
    OrderReturnProduct,
    ReturnAttachment,
    ReturnStatus,
)
from django_returns.utils.decorators import authorize_api
from django_returns.utils.pagination import paginate
from django_returns.worker.order_return import (
    mark_as_returned,
    send_email_return_confirmation,
    valid_order_to_return,
)


def cleanup_auxiliary_files(pdf_path):
    pdf_dir = os.path.dirname(pdf_path)
    files = os.listdir(pdf_dir)
    for file in files:
        if file.endswith(".aux") or file.endswith(".tex") or file.endswith(".log") or file.endswith(".pdf"):
            file_path = os.path.join(pdf_dir, file)
            os.remove(file_path)


def generate_and_save_pdf(table_data, return_obj):
    json_data = dict(settings.PDF_RETURN_TEMPLATE)
    document_variables = table_data

    pdf_name = f"return_{return_obj.pretty_id}"
    pdf_dir = os.path.join(settings.RETURN_DIR, str(return_obj.id))
    pdf_path = os.path.join(pdf_dir, pdf_name)

    os.makedirs(pdf_dir, exist_ok=True)

    pdf_generator = PDFGenerator(pdf_path, json_data, document_variables)
    pdf_generator.generate_pdf()

    with open(f"{pdf_path}.pdf", "rb") as pdf_file:
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_file.write(pdf_file.read())
        tmp_file.close()

    return_attachment = ReturnAttachment(order_return=return_obj)
    with open(tmp_file.name, "rb") as pdf_file:
        return_attachment.attachment.save(pdf_name, File(pdf_file))
        return_attachment.name = pdf_name
        return_attachment.save()

    os.remove(tmp_file.name)
    # cleanup_auxiliary_files(pdf_path)
    return return_attachment


def init_request(request, logger, channel_idx, order_id):
    customer = request.user.customer
    logger.add_log_param("channel_idx", channel_idx)
    logger.add_log_param("runned_at", datetime.now().isoformat())
    logger.add_log_param("customer_id", customer.id)
    logger.add_log_param("request_url", request.get_full_path())

    try:
        from django_checkout.models import Order, ProductRepresentation
    except ImportError:
        logger.set_code(4001)
        logger.error("Returns requires django_checkout app to be installed.")
        raise BadRequest("4001")

    try:
        order = Order.objects.get(order_id=order_id, customer=customer)
        channel = Channel.objects.get(idx=channel_idx)
        logger.add_log_param("order_id", order_id)
        logger.add_log_param("channel_idx", channel_idx)

    except Order.DoesNotExist:
        logger.set_code(4002)
        logger.error("Customer does not have order with this UUID.")
        raise NotFound("4002")
    except Channel.DoesNotExist:
        logger.set_code(4003)
        logger.error("Channel {channel_idx} does not exist.")
        raise NotFound("4003")
    return logger, order, customer, ProductRepresentation, channel


@api_view
@csrf_exempt
@authenticate
@authorize_api
@require_authentication
@require_http_method("POST", "GET")
def create_return(request, channel_idx: str, *args, **kwargs):
    customer = request.user.customer

    @parse_body(ReturnCreateRequest.Schema)
    def create_return(request, channel_idx: str, body: ReturnCreateRequest, *args, **kwargs):
        """
        Tworzy zwrot dla zamówienia.
        """
        logger = ProcessLogger("DJANGO_RETURNS_API_RETURN")
        logger, order, customer, ProductRepresentation, channel = init_request(
            request, logger, channel_idx, body.order_id
        )
        is_order_return_available, items_available_for_return, msg = valid_order_to_return(order, customer)
        if not is_order_return_available:
            logger.set_code(msg[0])
            logger.error(msg[1])
            raise BadRequest(msg[0])
        else:
            with transaction.atomic():
                products = []
                return_solutions_channel = [rm for rm in channel.return_solutions if rm["idx"] == body.return_solution]
                return_methods_channel = [rm for rm in channel.return_methods if rm["idx"] == body.return_method]
                if not return_methods_channel:
                    logger.set_code(4004)
                    logger.add_log_param("return_method", body.return_method)
                    logger.error(f"Return method {body.return_method} is not supported by this channel.")
                    raise BadRequest("4004")
                if not body.email:
                    logger.set_code(4012)
                    logger.error("Email is required")
                    raise BadRequest("4012")
                if not return_solutions_channel:
                    logger.set_code(4005)
                    logger.add_log_param("return_method", body.return_method)
                    logger.error(f"Return solution {body.return_solution} is not supported by this channel.")
                    raise BadRequest("4005")

                return_obj = None
                return_solution = channel.get_return_method_t9n(
                    idx=return_methods_channel[0].get("idx"), language=body.language
                )
                return_method = channel.get_return_solution_t9n(
                    idx=return_methods_channel[0].get("idx"), language=body.language
                )
                for product_sku, data in items_available_for_return.items():
                    for return_item in body.returned_items:
                        if return_item.sku == product_sku and return_item.quantity <= data["quantity"]:
                            try:
                                product_obj = ProductRepresentation.objects.get(
                                    sku=return_item.sku, channel__idx=channel_idx
                                )
                                if return_obj is None:
                                    return_obj = OrderReturn.objects.create(
                                        customer=customer,
                                        status=ReturnStatus.OPEN,
                                        order=order,
                                        return_method=body.return_method,
                                        return_solution=body.return_solution,
                                        comment=body.comment,
                                        email=body.email,
                                        bank_account_number=body.bank_account_number,
                                    )
                                OrderReturnProduct.objects.create(
                                    order_return=return_obj,
                                    product=product_obj,
                                    quantity=return_item.quantity,
                                    name=data["name"],
                                )
                                product_dict = asdict(return_item)
                                product_dict["name"] = data["name"]
                                products.append(product_dict)

                            except ProductRepresentation.DoesNotExist:
                                continue
                        else:
                            logger.set_code(3001)
                            logger.add_log_param_once("sku", return_item.sku)
                            logger.error(f"Product {return_item.sku} is not available for return.")

                if return_obj is not None:
                    return_obj.save()
                    formatted_date = datetime.now().strftime("%d %b %Y")
                    months = {
                        "Jan": "I",
                        "Feb": "II",
                        "Mar": "III",
                        "Apr": "IV",
                        "May": "V",
                        "Jun": "VI",
                        "Jul": "VII",
                        "Aug": "VIII",
                        "Sep": "IX",
                        "Oct": "X",
                        "Nov": "XI",
                        "Dec": "XII",
                    }
                    formatted_date = formatted_date.replace(formatted_date[3:6], months[formatted_date[3:6]])
                    order_data = [
                        [_("Data"), formatted_date],
                        [_("Numer zamówienia"), order.pretty_id],
                        [_("Sposób zwrotu towaru"), return_method],
                    ]
                    address_data = [
                        [_("Adres nadawczy"), _("Adres odbiorcy")],
                        [order.as_data.addresses.shipping_address.pretty_address(), channel.shop_shipping_address],
                    ]

                    products_data = [
                        [_("Produkt"), _("Powód"), _("Rozwiązanie"), _("Ilość")],
                        *[
                            [
                                f"Nazwa: {product['name']}\n SKU: {product['sku']}\n ",
                                body.comment if body.comment else "-",
                                return_solution if return_solution else "-",
                                str(product["quantity"]),
                            ]
                            for product in products
                        ],
                    ]

                    table_data = {
                        "table1": order_data,
                        "table2": address_data,
                        "table3": products_data,
                        "image1": channel.logo_on_document.path,
                        "text1": [body.comment] if body.comment else None,
                    }
                    customer_name = f"{order.as_data.addresses.shipping_address.firstname} {order.as_data.addresses.shipping_address.lastname}"
                    return_attachment = None
                    try:
                        return_attachment = generate_and_save_pdf(table_data, return_obj)
                        return_obj.return_attachment = return_attachment
                        return_obj.save()
                    except subprocess.CalledProcessError:
                        logger.set_code(4015)
                        logger.error("Error while generating pdf")
                    send_email_return_confirmation(
                        customer,
                        customer_name,
                        return_obj.pretty_id,
                        order.order_id,
                        body.comment,
                        order.pretty_id,
                        channel,
                        body.email,
                        body.language,
                        return_attachment,
                    )

                else:
                    logger.set_code(4009)
                    logger.error("None of the products are available for return.")
                    raise BadRequest("4009")

            mark_as_returned(order)
            final_data = model_to_dict(
                return_obj,
                exclude=["products", "customer", "order", "return_attachment", "return_method", "return_solution"],
            )
            final_data["returned_items"] = products
            final_data["order_id"] = order.order_id
            final_data["return_id"] = return_obj.id
            final_data["return_pretty_id"] = return_obj.pretty_id
            final_data["return_attachment_pk"] = (
                return_obj.return_attachment.pk if return_obj.return_attachment else None
            )
            final_data["return_method"] = {"idx": return_obj.return_method, "name": return_method}
            final_data["return_solution"] = {"idx": return_obj.return_solution, "name": return_solution}
            return Response(final_data)

    @parse_parameters(ReturnParams.Schema)
    def get_listing_returns(request, channel_idx: str, params: ReturnParams, *args, **kwargs):
        """
        Wyświetla uproszczoną listę zwrotów customera.
        """
        order_by = None
        if params.sort:
            sorters = reduce(lambda x, y: {**x, **y}, params.sort)
            order_by = []
            for sorter, direction in sorters.items():
                if direction.upper() == "ASC":
                    order_by.append(sorter)
                else:
                    order_by.append(f"-{sorter}")

        orders_return = OrderReturn.objects.filter(customer=customer)
        if order_by:
            orders_return = orders_return.order_by(*order_by)
        response_data = []
        for o_r in orders_return:
            attachments = ReturnAttachment.objects.filter(order_return=o_r)
            o_r_pk = None
            if o_r.return_attachment:
                o_r_pk = o_r.return_attachment.pk

            response_data.append(
                asdict(
                    ReturnListing(
                        return_id=o_r.id,
                        return_pretty_id=o_r.pretty_id,
                        created_at=o_r.created_at.strftime("%d/%m/%Y"),
                        order_pretty_id=o_r.order.pretty_id,
                        status=o_r.status,
                        attachments=[
                            {
                                "file_id": attachment.pk,
                                "name": attachment.name,
                                "path": attachment.get_download_url,
                                "is_return_pdf": True if o_r_pk == attachment.pk else False,
                            }
                            for attachment in attachments
                            if isinstance(attachment, ReturnAttachment)
                        ],
                    )
                )
            )

        pagination, paginated_data = paginate(request.GET, response_data)
        return PaginatedResponse(pagination, paginated_data)

    if request.method == "POST":
        return create_return(request, channel_idx, *args, **kwargs)
    else:
        return get_listing_returns(request, channel_idx, *args, **kwargs)


@api_view
@csrf_exempt
@authenticate
@authorize_api
@require_authentication
@require_http_method("GET")
def get_return_candidate(request, channel_idx: str, order_id: str, *args, **kwargs):
    logger = ProcessLogger("DJANGO_RETURNS_API_RETURN")
    logger, order, customer, ProductRepresentation, channel = init_request(request, logger, channel_idx, order_id)

    def get_return_candidate(request, channel: "Channel", *args, **kwargs):
        """
        Wyświetla i waliduje dane kandydata na zwrot.
        """
        is_order_return_available, items_available_for_return, msg = valid_order_to_return(order, customer)
        if not is_order_return_available:
            logger.set_code(msg[0])
            logger.error(msg[1])
            raise BadRequest(msg[0])
        else:
            return_response = ReturnResponse(
                order_id=order.order_id,
                address=order.as_data.addresses.shipping_address,
                items_returnable=items_available_for_return,
            )

        return Response(asdict(return_response))

    return get_return_candidate(request, channel, order, *args, **kwargs)


@api_view
@csrf_exempt
@authenticate
@authorize_api
@require_authentication
@require_http_method("GET")
def get_return_extra_data(request, channel_idx: str, order_id: str, *args, **kwargs):
    logger = ProcessLogger("DJANGO_RETURNS_API_RETURN")
    logger, order, customer, ProductRepresentation, channel = init_request(request, logger, channel_idx, order_id)

    @parse_parameters(GetReturnParams.Schema)
    def get_return_candidate(request, channel: "Channel", order_id: str, params: "GetReturnParams", *args, **kwargs):
        """
        Wyświetla i waliduje dane dodatkowe do kandydata na zwrot.
        """
        is_order_return_available, items_available_for_return, msg = valid_order_to_return(order, customer)
        if not is_order_return_available:
            logger.set_code(msg[0])
            logger.error(msg[1])
            raise BadRequest(msg[0])
        else:
            return_response = ReturnResponseExtra(
                return_solutions=channel.get_all_return_solutions_t9n(language=params.language),
                return_methods=channel.get_all_return_methods_t9n(language=params.language),
            )

        return Response(asdict(return_response))

    return get_return_candidate(request, channel, order, *args, **kwargs)


@api_view
@csrf_exempt
@authenticate
@authorize_api
@require_authentication
@require_http_method("GET", "PATCH", "POST")
def detail_return(request, channel_idx: str, return_id: str, *args, **kwargs):
    logger = ProcessLogger("DJANGO_RETURNS_API_RETURN")
    try:
        order_return = OrderReturn.objects.get(id=return_id)
        channel = Channel.objects.get(idx=channel_idx)
    except OrderReturn.DoesNotExist:
        logger.set_code(4010)
        logger.error("Customer does not have order with this UUID.")
        raise BadRequest("4010")
    logger, order, customer, ProductRepresentation, channel = init_request(
        request, logger, channel_idx, order_return.order.order_id
    )

    def post_attachment(request, channel_idx: str, *args, **kwargs):
        if "multipart/form-data" not in request.content_type:
            logger.set_code(4013)
            logger.error("Incorrect content-type. Set multipart/form-data")
            raise BadRequest("4013")
        all_attachments = request.FILES.keys()
        attachments = []
        for attachment in all_attachments:
            attachment_file = request.FILES.get(attachment)
            try:
                form_attachment_obj = ReturnAttachment.objects.create(
                    name=attachment_file.name, order_return=order_return, attachment=attachment_file
                )
                attachments.append(form_attachment_obj)
            except Exception as e:
                logger.exception(e)
                logger.set_code(4014)
                raise BadRequest(4014)
        if attachments:
            return Response(f"Successfully added {len(all_attachments)} attachments")
        else:
            raise BadRequest("4015")

    @parse_body(ReturnCreateRequest.Schema)
    def modify_return(request, channel: "Channel", return_id, body: ReturnCreateRequest, *args, **kwargs):
        is_order_return_available, items_available_for_return, msg = valid_order_to_return(
            order_return.order, customer, [order_return]
        )
        if not is_order_return_available:
            logger.set_code(msg[0])
            logger.error(msg[1])
            raise BadRequest(msg[0])
        else:
            if body.bank_account_number:
                order_return.bank_account_number = body.bank_account_number
            if body.comment:
                order_return.comment = body.comment
            if body.email:
                order_return.email = body.email
            if body.return_method:
                return_methods_channel = [rm for rm in channel.return_methods if rm["idx"] == body.return_method]
                if not return_methods_channel:
                    logger.set_code(4004)
                    logger.add_log_param("return_method", body.return_method)
                    logger.error(f"Return method {body.return_method} is not supported by this channel.")
                    raise BadRequest("4004")
                else:
                    order_return.return_method = body.return_method
            if body.return_solution:
                return_solutions_channel = [rm for rm in channel.return_solutions if rm["idx"] == body.return_solution]
                if not return_solutions_channel:
                    logger.set_code(4005)
                    logger.add_log_param("return_method", body.return_method)
                    logger.error(f"Return solution {body.return_solution} is not supported by this channel.")
                    raise BadRequest("4005")
                else:
                    order_return.return_solution = body.return_solution

            if body.returned_items:
                with transaction.atomic():
                    order_to_delete = list(
                        OrderReturnProduct.objects.filter(order_return=order_return).values_list("pk", flat=True)
                    )
                    products = []
                    for product_sku, data in items_available_for_return.items():
                        for return_item in body.returned_items:
                            if return_item.sku == product_sku and return_item.quantity <= data["quantity"]:
                                try:
                                    product_obj = ProductRepresentation.objects.get(
                                        sku=return_item.sku, channel__idx=channel.idx
                                    )
                                    obj = OrderReturnProduct.objects.create(
                                        order_return=order_return,
                                        product=product_obj,
                                        quantity=return_item.quantity,
                                        name=data["name"],
                                    )
                                    product_dict = asdict(return_item)
                                    product_dict["name"] = data["name"]
                                    products.append(product_dict)
                                except ProductRepresentation.DoesNotExist:
                                    continue
                            else:
                                logger.set_code(3001)
                                logger.add_log_param_once("sku", return_item.sku)
                                logger.error(f"Product {return_item.sku} is not available for return.")

                    if products:
                        OrderReturnProduct.objects.filter(pk__in=order_to_delete).delete()
                    else:
                        raise BadRequest("4009")
            order_return.save()

            return_solution = channel.get_return_method_t9n(idx=order_return.return_method, language=body.language)
            return_method = channel.get_return_solution_t9n(idx=order_return.return_method, language=body.language)
            final_data = model_to_dict(
                order_return,
                exclude=["products", "customer", "order", "return_attachment", "return_method", "return_solution"],
            )
            final_data["returned_items"] = products
            final_data["order_id"] = order.order_id
            final_data["return_id"] = order_return.id
            final_data["return_pretty_id"] = order_return.pretty_id
            final_data["return_attachment_pk"] = (
                order_return.return_attachment.pk if order_return.return_attachment else None
            )
            final_data["return_method"] = {"idx": order_return.return_method, "name": return_method}
            final_data["return_solution"] = {"idx": order_return.return_solution, "name": return_solution}

            return Response(final_data)

    @parse_parameters(GetReturnParams.Schema)
    def get_detail_return(request, channel: "Channel", return_id, params: GetReturnParams, *args, **kwargs):
        """
        Wyświetla dane szczegółowe zwrotu.
        """
        return_method = channel.get_return_method_t9n(idx=order_return.return_method, language=params.language)
        return_solution = channel.get_return_solution_t9n(idx=order_return.return_solution, language=params.language)
        order_return_listing = OrderReturnListing(
            return_pretty_id=order_return.pretty_id,
            return_id=order_return.id,
            created_at=order_return.created_at.strftime("%d/%m/%Y"),
            status=order_return.status,
            address=order_return.order.as_data.addresses.shipping_address,
            return_solution={"name": return_solution, "idx": order_return.return_solution},
            return_attachment_pk=order_return.return_attachment.pk if order_return.return_attachment else None,
            comment=order_return.comment if order_return.comment else None,
            bank_account_number=order_return.bank_account_number if order_return.bank_account_number else None,
            order_id=order_return.order.order_id,
            order_pretty_id=order_return.order.pretty_id,
            return_method={"name": return_method, "idx": order_return.return_method},
            returned_items=[
                {"sku": item["product__sku"], "quantity": item["quantity"], "name": item["name"]}
                for item in OrderReturnProduct.objects.filter(order_return=order_return).values(
                    "product__sku", "quantity", "name"
                )
            ],
        )
        return Response(asdict(order_return_listing))

    if request.method == "PATCH":
        return modify_return(request, channel, return_id, *args, **kwargs)
    elif request.method == "POST":
        return post_attachment(request, channel_idx, return_id, *args, **kwargs)
    else:
        return get_detail_return(request, channel, return_id, *args, **kwargs)


def download_return_file_view(request, pk):
    order_return = OrderReturn.objects.filter(id=pk).first().return_attachment
    if (
        request.user.is_superuser
        or request.user.has_perm("django_returns.view_returnattachment")
        or request.user.has_perm("django_returns.view_orderreturn")
        and order_return
    ):
        return FileResponse(order_return.attachment)
    else:
        return HttpResponse("Unauthorized", status=401)


def download_attachment_view(request, pk):
    return_attachment = ReturnAttachment.objects.filter(id=pk).first()
    if (
        request.user.is_superuser
        or request.user.has_perm("django_returns.view_returnattachment")
        or request.user.has_perm("django_returns.view_orderreturn")
        and return_attachment
    ):
        return FileResponse(return_attachment.attachment)
    else:
        return HttpResponse("Unauthorized", status=401)
