# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django_checkout.enums import OrderStatus
from django_checkout.models import Order
from django_email.service.returns.return_confirmation import ReturnConfirmationEmail

from django_returns import settings
from django_returns.models import OrderReturnProduct


def valid_order_to_return(order: Order, customer, skip_return: str = None) -> (bool, dict):
    """
    Walidacja zamówienia pod kątem możliwości utworzenia zwrotu. Zwraca krotkę (bool, list), gdzie:
    - bool: czy zamówienie jest możliwe do zwrotu
    - dict: słownik produktów, które można zwrócić {'MAX-36-Czarny': Decimal('3')}
    """

    order_return_products = OrderReturnProduct.objects.filter(order_return__order=order)
    if skip_return:
        order_return_products = order_return_products.exclude(order_return__in=skip_return)
    product_quantities = order_return_products.values("product__sku").annotate(total_quantity=Sum("quantity"))

    items_in_cart = {item.sku: (item.quantity, item.name) for item in order.as_data.cart.items}
    already_returned_items = {item["product__sku"]: Decimal(item["total_quantity"]) for item in product_quantities}

    # walidowanie 1: czy użytkownik posiada to zamówienie
    if order.customer != customer:
        return False, {}, (4002, "Customer does not have order with this UUID.")

    # walidowanie 2: order_status=complete,
    if order.order_status != OrderStatus.COMPLETED:
        return False, {}, (4006, "Order is not completed or is fully returned")

    # walidowanie 4: bierzemy tylko pod uwagę zamówienia nie starsze niż X dni (settings, domyślnie 14)
    if order.order_status == OrderStatus.COMPLETED and order.in_status_since < timezone.now() - timezone.timedelta(
        days=settings.DAYS_TO_RETURN
    ):
        return False, {}, (4007, "Order is too old to return")

    # walidowanie 4: czy zamówienie posiada choć jedną linie możliwą do zwrotu
    items_available_for_return = {}
    # Zbiór items_in_cart - already_returned_items
    for key, value in items_in_cart.items():
        if key in already_returned_items:
            result = value[0] - already_returned_items[key]
            if result >= 1:
                items_available_for_return[key] = {"quantity": result, "name": value[1]}
        else:
            items_available_for_return[key] = {"quantity": value[0], "name": value[1]}
    if items_available_for_return:
        return True, items_available_for_return, (200, "success")
    else:
        order.order_status = OrderStatus.RETURNED
        order.save()
        return False, {}, (4008, "Order does not have any items available for return")


def mark_as_returned(order):
    order_return_products = OrderReturnProduct.objects.filter(order_return__order=order)
    product_quantities = order_return_products.values("product__sku").annotate(total_quantity=Sum("quantity"))
    already_returned_items = {item["product__sku"]: Decimal(item["total_quantity"]) for item in product_quantities}
    items_in_cart = {item.sku: item.quantity for item in order.as_data.cart.items}
    items_available_for_return = {}
    for key, value in items_in_cart.items():
        if key in already_returned_items:
            result = value - already_returned_items[key]
            if result >= 1:
                items_available_for_return[key] = result
        else:
            items_available_for_return[key] = value

    if not items_available_for_return:
        order.order_status = OrderStatus.RETURNED
        order.save()


def send_email_return_confirmation(
    customer, customer_name, return_id, order_id, comment, order_pretty_id, channel, email, lang, return_attachment=None
):
    return_confirmation_email = ReturnConfirmationEmail(
        exception_type=ReturnConfirmationEmail.ExceptionType.API, language=lang, channel_idx=channel.idx
    )
    if return_attachment:
        attachment = return_confirmation_email.build_attachment(
            path=return_attachment.attachment.path, name=return_attachment.name, ext="pdf"
        )
    else:
        attachment = None

    emails = [email, channel.email_administrator]
    for email in emails:
        return_confirmation_email.send(
            [email],
            first_name=customer.user.first_name,
            last_name=customer.user.last_name,
            customer_name=customer_name,
            customer_username=customer.user.username,
            customer_email=customer.user.email,
            return_id=return_id,
            order_id=order_id,
            order_pretty_id=order_pretty_id,
            shop_shipping_address=channel.shop_shipping_address,
            comment=comment,
            attachments=[attachment],
        )
