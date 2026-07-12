# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django_admin_inline_paginator.admin import TabularInline

from django_returns.models import APIKey, Channel, OrderReturn, OrderReturnProduct, ReturnAttachment


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
    list_display = ["key", "created_at", "modified_at"]
    readonly_fields = ["key", "created_at", "modified_at"]
    search_fields = ["key"]
    list_filter = ["created_at", "modified_at"]
    ordering = ["-created_at"]
    actions = ["generate_new_key"]


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
