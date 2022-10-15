# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile cu diferenta de pret

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockCommonPriceDiff(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["account.move.line"]._l10n_ro_get_or_create_price_difference_product()
