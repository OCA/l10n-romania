# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.tests import tagged

from .common import TestStockCommonPriceDiff


@tagged("post_install", "-at_install")
class TestStockPurchaseDozen(TestStockCommonPriceDiff):
    def test_dozen_uom_nir_with_invoice_and_no_diff(self):
        """
        Receptie produs product_1 in unitate de masura Dozen,
        qty = 1, PO uom = Dozen (12 Units), price_unit = 12

        Factura qty = 1, UOM Dozen, price_unit = 12 (doar pt product_1)
        => Nu exista diferenta
        """
        self._setup_dozen()

        po = self.create_po(validate_picking=False)

        qty_done_p1 = self.product_1.uom_po_id._compute_quantity(
            self.qty_po_p1, self.product_1.uom_id
        )
        qty_done_p2 = self.product_2.uom_po_id._compute_quantity(
            self.qty_po_p2, self.product_2.uom_id
        )
        picking = po.picking_ids.filtered(lambda pick: pick.state != "done")
        for move_line in picking.move_line_ids:
            if move_line.product_id == self.product_1:
                move_line.write({"qty_done": qty_done_p1})
            if move_line.product_id == self.product_2:
                move_line.write({"qty_done": qty_done_p2})

        picking.button_validate()
        picking._action_done()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        po.action_create_invoice()
        aml = self.env["account.move.line"].search(
            [("purchase_line_id", "in", po.order_line.ids)]
        )
        invoice = aml.mapped("move_id")
        invoice.write({"invoice_date": fields.Date.today()})
        invoice.action_post()
        diff_wiz = self.env["l10n_ro.price_difference_confirm_dialog"].search(
            [("invoice_id", "=", invoice.id)]
        )
        if diff_wiz:
            diff_wiz.action_confirm()

        # stocul  are valoarea fara diferenta
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

    def test_purchase_eur_dozen_uom_nir_with_invoice_and_diff(self):
        self._setup_dozen()

        self.create_po_default(
            {
                "currency": self.currency_eur,
            }
        )

        ron_value1 = self.qty_po_p1 * self.price_p1 * self.rate
        ron_value2 = self.qty_po_p2 * self.price_p2 * self.rate

        ron_value_f1 = self.qty_po_p1 * (self.price_p1 + self.diff_p1) * self.rate
        ron_value_f2 = self.qty_po_p2 * (self.price_p2 + self.diff_p2) * self.rate

        self.check_stock_valuation(ron_value1, ron_value2)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice(self.diff_p1, self.diff_p2)
        # in stocul  are valoarea cu diferenta de pret inregistrata

        self.check_stock_valuation(ron_value_f1, ron_value_f2)

        # in contabilitate stocul este inregistrat cu diferentele de pret
        self.check_account_valuation(ron_value_f1, ron_value_f2)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)
