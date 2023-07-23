# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)
# Generare note contabile la achizitie


@tagged("post_install", "-at_install")
class TestStockPurchase(TestStockCommon):
    def test_nir_with_notice_and_invoice(self):
        """
        Receptie produse pe baza de aviz si inregistare
        ulterioara a facturii
        """
        self.create_po(vals={"l10n_ro_notice": True})

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # soldul lui 408 trebuie sa fie zero
        self.check_account_valuation(0, 0, self.stock_picking_payable_account_id)
