# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = getattr(settings, "API_BASE_URL", "api").strip("/")

# CUSTOMER FILES
PRIVATE_DIR = getattr(settings, "PRIVATE_DIR", None)
if not PRIVATE_DIR:
    raise OSError("Setting PRIVATE_DIR is not set. Default should be '/private'.")
RETURN_DIR = os.path.join(PRIVATE_DIR, "returns/")
# RETURN_CONFIRMATION_EMAIL_TEMPLATE_PATH_HTML - is path to email template -  html
RETURN_CONFIRMATION_EMAIL_TEMPLATE_PATH_HTML = getattr(
    settings, "NEW_ACCOUNT_EMAIL_TEMPLATE_PATH_HTML", "django_returns/email/default_return.html"
)
# RETURN_CONFIRMATION_EMAIL_TEMPLATE_PATH_TXT - is path to email template -  txt
RETURN_CONFIRMATION_TEMPLATE_PATH_TXT = getattr(
    settings, "NEW_ACCOUNT_EMAIL_TEMPLATE_PATH_HTML", "django_returns/email/default_return.txt"
)

# LOGO_URL - is url to logo which will be used in email templates
EMAIL_LOGO_URL = getattr(settings, "LOGO_URL", "")

# DEFAULT_FROM_EMAIL - is email address from which emails will be send
DEFAULT_FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", None)
# TEMPLATE_DIRS - is path to email templates
TEMPLATE_DIRS = os.path.join(BASE_DIR, "/templates/django_returns/email/")
DAYS_TO_RETURN = getattr(settings, "DAYS_TO_RETURN", 14)

PDF_RETURN_TEMPLATE_DEFAULT = {
    "geometry_options": {"tmargin": "1cm", "lmargin": "1cm"},
    "document_info": {},
    "document_contents": [
        {"type": "top_line", "extra": {"width": "1pt", "color": "black"}, "position": "center"},
        {"type": "fill_line", "multiplier": 1},
        {"type": "image", "data_variable": "image1", "extra": {"width": "8cm"}, "position": "right"},
        {
            "type": "h1",
            "content": "Zwrot towaru z platformy internetowej.",
            "extra": {"numbering": False},
            "position": "left",
        },
        {"type": "fill_line", "multiplier": 2},
        {
            "type": "tabularx",
            "data_variable": "table1",
            "add_hline": True,
            "bolt_headers": False,
            "extra": {"booktabs": False},
            "position": "center",
        },
        {"type": "fill_line", "multiplier": 1},
        {
            "type": "tabularx",
            "data_variable": "table2",
            "add_hline": True,
            "bolt_headers": True,
            "extra": {"booktabs": False},
            "position": "center",
        },
        {"type": "fill_line", "multiplier": 2},
        {"type": "h1", "content": "Komentarze", "extra": {"numbering": False}, "position": "left"},
        {"type": "fill_line", "multiplier": 1},
        {"type": "list_itemize", "data_variable": "text1", "position": "left"},
        {"type": "fill_line", "multiplier": 1},
        {
            "type": "tabularx",
            "data_variable": "table3",
            "add_hline": True,
            "bolt_headers": True,
            "extra": {"booktabs": False},
            "position": "center",
        },
    ],
}
PDF_RETURN_TEMPLATE = getattr(settings, "PDF_RETURN_TEMPLATE", PDF_RETURN_TEMPLATE_DEFAULT)
