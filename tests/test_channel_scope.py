# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A request reads the customer's orders and returns of the URL's channel only, and sorts by listed fields only.

The key is checked against the channel of the URL, so the data loaded for the customer has to stay in that channel
too. Views are called directly (the module's test settings have no ROOT_URLCONF).
"""

import json

import pytest
from django.test import RequestFactory
from django_accounts.models import Customer
from django_checkout.models import Channel as CheckoutChannel
from django_checkout.models import Order
from django_regional.models import Country, Currency, Language

from django_returns.models import Channel, OrderReturn
from django_returns.views.order_return import create_return, detail_return, get_return_candidate

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("_jwt_backend")]

HERE, ELSEWHERE = "shop-here", "shop-elsewhere"


def _checkout_channel(idx: str) -> CheckoutChannel:
    language, _ = Language.objects.get_or_create(iso2="en", defaults={"iso3": "eng", "name_en": "English"})
    currency, _ = Currency.objects.get_or_create(iso3="EUR", defaults={"name_en": "Euro"})
    if not Country.objects.filter(iso2="PL").exists():  # Country.save() is blocked (seed model)
        Country.objects.bulk_create([Country(iso2="PL", iso3="POL", name_en="Poland", name_pl="Polska")])
    country = Country.objects.get(iso2="PL")
    Channel.objects.create(idx=idx, label=idx)
    return CheckoutChannel.objects.create(
        idx=idx, label=idx, min_order_price=0, default_language=language, default_currency=currency,
        default_country=country,
    )  # fmt: skip


@pytest.fixture
def returns(customer_jwt) -> dict[str, OrderReturn]:
    """One return of the customer in each of two channels."""
    customer = Customer.objects.get(user__username="returner")
    made = {}
    for idx in (HERE, ELSEWHERE):
        order = Order.objects.create(channel=_checkout_channel(idx), customer=customer, order_body={})
        made[idx] = OrderReturn.objects.create(order=order, customer=customer)
    return made


@pytest.fixture
def get(customer_jwt, make_api_key):
    """Call a keyed view as the customer on a channel; returns ``(status, data)``."""
    headers = {"HTTP_X_API_KEY": make_api_key(), "HTTP_AUTHORIZATION": f"Bearer {customer_jwt}"}

    def get(view, channel_idx: str = HERE, query: str = "", **kwargs) -> tuple[int, object]:
        request = RequestFactory().get(f"/returns/{query}", **headers)
        response = view(request, channel_idx=channel_idx, version="1", **kwargs)
        return response.status_code, json.loads(response.content)["data"]

    return get


def _listed(data: list[dict]) -> list[str]:
    return [item["return_id"] for item in data]


def test_listing_holds_the_returns_of_the_urls_channel_only(get, returns):
    status, data = get(create_return)
    assert status == 200
    assert _listed(data) == [str(returns[HERE].id)]


def test_return_of_another_channel_is_not_found(get, returns):
    assert get(detail_return, return_id=str(returns[ELSEWHERE].id)) == (404, "4002")


def test_order_of_another_channel_is_not_found(get, returns):
    assert get(get_return_candidate, order_id=str(returns[ELSEWHERE].order.order_id)) == (404, "4002")


@pytest.mark.parametrize(("direction", "first"), [("ASC", "older"), ("DESC", "newer")])
def test_listing_sorts_by_a_listed_field(get, returns, direction, first):
    newer = OrderReturn.objects.create(order=returns[HERE].order, customer=returns[HERE].customer)
    ids = {"older": str(returns[HERE].id), "newer": str(newer.id)}
    status, data = get(create_return, query=f'?sort={{"created_at":"{direction}"}}')
    assert status == 200
    assert _listed(data)[0] == ids[first]


@pytest.mark.parametrize("field", ["customer__user__password", "order__order_body", "-created_at", "nope"])
def test_listing_refuses_a_sort_field_outside_the_list(get, returns, field):
    assert get(create_return, query=f'?sort={{"{field}":"ASC"}}') == (400, "4016")
