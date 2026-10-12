# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from django_admin_inline_paginator.admin import TabularInline

from django_returns.models import APIKey, Channel, OrderReturn, OrderReturnProduct, ReturnAttachment
from django_returns.utils.api_keys import access_installed, mask_key


class OrderReturnProductInline(TabularInline):
    model = OrderReturnProduct
    readonly_fields = ["id"]
    extra = 0
    ordering = ("-modified_at",)
    autocomplete_fields = ["order_return", "product"]


@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    inlines = [OrderReturnProductInline]
    model = OrderReturn
    list_display = ["id", "order", "status", "created_at", "modified_at", "download_file"]
    autocomplete_fields = ["customer", "return_attachment"]
    search_fields = ["id", "order__id", "customer__uid", "pretty_id"]
    list_filter = ["status", "created_at", "modified_at"]
    readonly_fields = ["id", "created_at", "modified_at", "bank_account_number", "pretty_id"]

    def download_file(self, obj):
        obj_attachment = ReturnAttachment.objects.filter(order_return=obj).first()
        if obj_attachment and obj_attachment.attachment and obj_attachment.attachment.url:
            url = reverse("order-return-download", args=[obj.pk])
            return format_html('<a class="button" href="{}">Pobierz</a>', url)
        return "Brak pliku"

    download_file.short_description = "Plik"


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["idx", "label"]


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """The list masks keys on both paths; with django_access installed the change page masks them and is read-only."""

    list_display = ["masked_key", "created_at", "modified_at"]
    list_filter = ["created_at", "modified_at"]
    ordering = ["-created_at"]

    def get_readonly_fields(self, request: HttpRequest, obj: APIKey | None = None) -> list[str]:
        return ["masked_key" if access_installed() else "key", "created_at", "modified_at"]

    @admin.display(description="key")
    def masked_key(self, obj: APIKey) -> str:
        return mask_key(obj.key)

    def has_add_permission(self, request) -> bool:
        return not access_installed() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None) -> bool:
        return not access_installed() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None) -> bool:
        return not access_installed() and super().has_delete_permission(request, obj)


@admin.register(ReturnAttachment)
class ReturnAttachmentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "order_return", "download_file"]
    readonly_fields = ["id", "created_at", "modified_at"]
    search_fields = ["id", "name", "path", "order_return"]
    list_filter = ["created_at", "modified_at"]

    def download_file(self, obj):
        if obj.attachment and obj.attachment.url:
            url = reverse("order-attachment-download", args=[obj.pk])
            return format_html('<a class="button" href="{}">Pobierz</a>', url)
        return "Brak pliku"

    download_file.short_description = "Plik"
