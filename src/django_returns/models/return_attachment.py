# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.core.files.storage import FileSystemStorage
from django.db import models

from django_returns import settings
from django_returns.models import OrderReturn
from django_returns.models.base_model import BaseModel


def order_directory_path(instance, filename):
    return f"{instance.order_return.id}/{filename}"


def order_storage():
    return FileSystemStorage(location=settings.RETURN_DIR)


class ReturnAttachment(BaseModel):
    name = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text="It will automatically be filled in with the file name when saving",
    )
    order_return: "OrderReturn" = models.ForeignKey("OrderReturn", null=True, on_delete=models.PROTECT)
    attachment = models.FileField(blank=False, null=False, upload_to=order_directory_path, storage=order_storage)
    objects = models.Manager()

    @property
    def get_download_url(self):
        return f"/returns/{self.order_return.id}/file/{self.pk}/customer/{self.order_return.order.customer.uid}"

    def save(self, *args, **kwargs):
        # self.name = self.attachment.name
        super().save(*args, **kwargs)
