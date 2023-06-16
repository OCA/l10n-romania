# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

import logging

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
        

    # def check_account_valuation(self, val_p1, val_p2, account=None):
    #     val_p1 = round(val_p1, 2)
    #     val_p2 = round(val_p2, 2)
    #     if not account:
    #         account = self.account_valuation
    #
    #     domain = [
    #         ("product_id", "in", [self.product_1.id, self.product_2.id]),
    #         ("account_id", "=", account.id),
    #         ("parent_state", "=", "posted"),
    #     ]
    #     account_valuations = self.env["account.move.line"].read_group(
    #         domain, ["debit:sum", "credit:sum", "quantity:sum"], ["product_id"]
    #     )
    #     d = self.env["account.move.line"].search(domain)
    #     _logger.error(f"------------------{domain, account_valuations, val_p1, val_p2, account}--------------------------")
    #     for valuation in account_valuations:
    #         val = round(valuation["debit"] - valuation["credit"], 2)
    #         _logger.error(f"i8 {val, valuation['product_id'][0], self.product_1.id}")
    #         if valuation["product_id"][0] == self.product_1.id:
    #             _logger.debug("Check account P1 {} = {}".format(val, val_p1))
    #             self.assertAlmostEqual(val, val_p1)
    #         _logger.error(f"i9 {val, valuation['product_id'][0] == self.product_2.id}")
    #         if valuation["product_id"][0] == self.product_2.id:
    #             _logger.debug("Check account P2 {} = {}".format(val, val_p2))
    #             self.assertAlmostEqual(val, val_p2)
