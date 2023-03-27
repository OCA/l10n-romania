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

    def _setup_dozen(self):
        self.product_1.uom_id = self.env.ref("uom.product_uom_unit")
        self.product_1.uom_po_id = self.env.ref("uom.product_uom_dozen")
        self.qty_po_p1 = 1
        self.price_p1 = 12

        self.diff_p1 = 0
        self.diff_p2 = 0

        self.product_2.uom_po_id = self.env.ref("uom.product_uom_dozen")
        self.qty_po_p2 = 1
        self.price_p2 = 12

        self.val_p1_i = round(self.qty_po_p1 * self.price_p1, 2)
        self.val_p2_i = round(self.qty_po_p2 * self.price_p2, 2)

        self.val_p1_f = round(self.qty_po_p1 * (self.price_p1 + self.diff_p1), 2)
        self.val_p2_f = round(self.qty_po_p2 * (self.price_p2 + self.diff_p2), 2)
