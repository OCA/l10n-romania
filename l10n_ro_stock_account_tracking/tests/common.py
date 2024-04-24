# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie

import logging

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import (
    TestStockCommon as TestStockCommonBase,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCommon(TestStockCommonBase):
    pass
