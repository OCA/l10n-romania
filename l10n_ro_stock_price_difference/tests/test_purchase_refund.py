# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.tests import tagged

from .common import TestStockCommonPriceDiff


@tagged("post_install", "-at_install")
class TestStockPurchaseRefund(TestStockCommonPriceDiff):
    def test_nir_with_invoice_and_refund_partial_no_difference(self):
        po = self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice(auto_post=False)

        pick = po.picking_ids
        self.make_return(pick, 5)
        stock_value_final_p1 = self.val_p1_i / 2
        stock_value_final_p2 = self.val_p2_i / 2
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)

        self.check_account_valuation(0.0, 0.0)

        self.invoice.action_post()

        # in stocul  are valoarea cu diferenta de pret inregistrata
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

        po.action_create_invoice()
        po.invoice_ids[-1].invoice_date = fields.Date.today()
        po.invoice_ids[-1].action_post()

        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)

    def test_nir_with_invoice_and_total_refund_no_difference(self):
        po = self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice()

        pick = po.picking_ids
        self.make_return(pick, 10)

        self.check_stock_valuation(0.0, 0.0)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

        po.action_create_invoice()
        po.invoice_ids[-1].invoice_date = fields.Date.today()
        po.invoice_ids[-1].action_post()

        self.check_account_valuation(0.0, 0.0)
        self.check_stock_valuation(0.0, 0.0)
        self.check_account_diff(0, 0)
