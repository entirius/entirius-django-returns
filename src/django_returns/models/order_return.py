# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from django_checkout.models import Order, ProductRepresentation

from .base_model import BaseModel


class ReturnStatus(TextChoices):
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")

    @staticmethod
    def map(choice: int) -> str:
        match choice:
            case ReturnStatus.OPEN:
                return 1
            case ReturnStatus.CLOSED:
                return 2
            case _:
                return None


class OrderReturn(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    products: "ProductRepresentation" = models.ManyToManyField(
        "django_checkout.ProductRepresentation",
        related_name="order_return_products",
        blank=False,
        through="OrderReturnProduct",
    )
    order: Order = models.ForeignKey("django_checkout.Order", on_delete=models.CASCADE, related_name="returns_order")
    status = models.CharField(max_length=256, choices=ReturnStatus.choices, default=ReturnStatus.OPEN)
    customer = models.ForeignKey("django_accounts.Customer", on_delete=models.CASCADE, related_name="returns_customer")
    return_method = models.CharField(max_length=256, blank=True, null=True)
    return_solution = models.CharField(max_length=256, blank=True, null=True)
    return_attachment = models.ForeignKey("ReturnAttachment", on_delete=models.CASCADE, blank=True, null=True)
    comment = models.TextField(blank=True, null=True, max_length=300)
    email = models.EmailField(blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    objects = models.Manager()

    @property
    def return_in_order_id(self):
        return self.order.returns_order.filter(created_at__lte=self.created_at).count()

    @property
    def pretty_id(self):
        left = str(self.return_in_order_id).zfill(3)
        right = self.order.pretty_id
        return f"{left}{right}"


class OrderReturnProduct(BaseModel):
    order_return: "OrderReturn" = models.ForeignKey(on_delete=models.deletion.CASCADE, to="OrderReturn")
    product: "ProductRepresentation" = models.ForeignKey(
        on_delete=models.deletion.CASCADE, to="django_checkout.productrepresentation"
    )
    name = models.CharField(max_length=256, blank=True, null=True)
    quantity = models.PositiveSmallIntegerField(blank=False, null=False)
    objects = models.Manager()
