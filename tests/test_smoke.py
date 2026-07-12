# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Smoke test: every public submodule imports cleanly under a configured Django."""

import importlib

import pytest

MODULES = [
    "django_returns.apps",
    "django_returns.settings",
    "django_returns.models",
    "django_returns.models.api_key",
    "django_returns.models.channel",
    "django_returns.models.order_return",
    "django_returns.models.return_attachment",
    "django_returns.admin",
    "django_returns.bi",
    "django_returns.domain.dto.order_return",
    "django_returns.urls",
    "django_returns.utils.decorators",
    "django_returns.utils.pagination",
    "django_returns.views.order_return",
    "django_returns.views.return_attachment",
    "django_returns.worker.order_return",
    "django_returns.management.commands.returns-generate-api-key",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)
