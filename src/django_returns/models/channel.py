# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_returns.models.base_model import BaseModel


class Channel(BaseModel):
    idx = models.CharField(max_length=128, blank=False, null=False, unique=True)
    label = models.CharField(max_length=128, blank=False, null=False, default="", unique=True)
    return_methods = models.JSONField(blank=True, null=True)
    return_solutions = models.JSONField(blank=True, null=True)
    logo_on_document = models.ImageField(upload_to="pic", null=True, blank=True)
    shop_shipping_address = models.TextField(max_length=1024, blank=True, null=True)
    email_administrator = models.EmailField(blank=True, null=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.label} [{self.idx}]"

    class Meta:
        ordering = []
        verbose_name_plural = "Returns - channels"

    def get_all_return_methods_t9n(self, language="pl"):
        # self.return_methods = [{"idx": "send_myself", "name": {"de": "Selbstversand", "en": "Send Myself", "fr": "Envoyer moi-même", "pl": "Sam wyślę produkt"}}]
        for rm in self.return_methods:
            rm["name"] = rm["name"].get(language, "")
        return self.return_methods

    def get_all_return_solutions_t9n(self, language="pl"):
        # self.return_methods = [{"idx": "return", "name": {"de": "Rückgabe", "en": "Return", "fr": "Retour", "pl": "Zwrot środków"}},
        #  {"idx": "exchange", "name": {"de": "Austausch", "en": "Exchange", "fr": "Échange", "pl": "Wymiana produktów"}},
        #  {"idx": "voucher", "name": {"de": "Gutschein", "en": "Voucher", "fr": "Bon d'achat", "pl": "Voucher"}}]

        for rm in self.return_solutions:
            rm["name"] = rm["name"].get(language, "")
        return self.return_solutions

    def get_return_method_t9n(self, idx, language="pl"):
        for rm in self.return_methods:
            if rm["idx"] == idx:
                return rm["name"].get(language, "")
        return ""

    def get_return_solution_t9n(self, idx, language="pl"):
        for rm in self.return_solutions:
            if rm["idx"] == idx:
                return rm["name"].get(language, "")
        return ""
