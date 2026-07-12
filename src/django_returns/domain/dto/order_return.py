# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from dataclasses import field
from itertools import groupby

import marshmallow.validate
from django_checkout.domain.dto.address import Address
from marshmallow import fields, pre_load
from marshmallow_dataclass import add_schema, dataclass


@add_schema
@dataclass
class Sorter:
    order: str


@add_schema
@dataclass
class ReturnSolution:
    idx: str
    name: str


@add_schema
@dataclass
class ReturnMethod:
    idx: str
    name: str


@add_schema
@dataclass
class ReturnItem:
    sku: str
    quantity: int
    name: str = None


@add_schema
@dataclass
class ReturnParams:
    page: int = 1
    limit: int = 10
    sort: list[dict] | None = None

    @pre_load
    def handle_sort(self, data, **kwargs):
        if "sort" in data:
            result = {**data}
            result["sort"] = [json.loads(elem) for elem in result.get("sort")]
            return result
        return data

    @pre_load
    def handle_parameter_list(self, data, **kwargs):
        """Aggregate values from list like parameters, for example from sku and sku[], into one field"""
        key_func = lambda x: x.strip("[]")
        grouped = groupby(sorted(data, key=key_func), key=key_func)
        result = {}
        for key, group in grouped:
            acc = []
            for elem in group:
                acc.extend(data.getlist(elem))

            field = self.declared_fields.get(key)
            if field is None:
                continue
            if isinstance(field, fields.List):
                result[key] = acc
            else:
                result[key] = acc[0]
        return result


@add_schema
@dataclass
class ReturnResponse:
    # 3
    order_id: str
    address: Address
    items_returnable: list[ReturnItem]


@add_schema
@dataclass
class ReturnResponseExtra:
    return_solutions: list[ReturnSolution]
    return_methods: list[ReturnMethod]


@add_schema
@dataclass
class ReturnCreateRequest:
    # 4 i 5
    order_id: str | None
    returned_items: list[ReturnItem] | None
    return_method: str | None
    return_solution: str | None
    email: str | None = field(metadata={"validate": marshmallow.validate.Email()})
    language: str
    bank_account_number: str | None = field(metadata={"validate": marshmallow.validate.Length(max=50)})
    comment: str | None = field(metadata={"validate": marshmallow.validate.Length(max=300)})


@add_schema
@dataclass
class GetReturnParams:
    language: str


@add_schema
@dataclass
class ReturnAttachments:
    file_id: str
    name: str
    path: str


@add_schema
@dataclass
class ReturnListing:
    # 6
    return_id: str
    created_at: str
    return_pretty_id: str
    order_pretty_id: str
    status: str
    attachments: list[ReturnAttachments] | None


@add_schema
@dataclass
class OrderReturnListing:
    # 7
    return_id: str
    return_pretty_id: str
    created_at: str
    order_pretty_id: str
    status: str
    bank_account_number: str | None = field(metadata={"validate": marshmallow.validate.Length(max=50)})
    return_attachment_pk: int | None
    comment: str | None = field(metadata={"validate": marshmallow.validate.Length(max=300)})
    order_id: str
    address: Address
    return_solution: ReturnSolution
    return_method: ReturnMethod
    returned_items: list[ReturnItem]
