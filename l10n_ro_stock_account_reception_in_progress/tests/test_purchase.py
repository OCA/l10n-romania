# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_price_difference.tests.common import (
    TestStockCommonPriceDiff,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockPurchase(TestStockCommonPriceDiff):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.acc_327 = cls.env["account.account"].search(
            [("code", "=", "327000")], limit=1
        )
        cls.account_valuation.l10n_ro_reception_in_progress_account_id = cls.acc_327

    def create_po(self, picking_type_in=None, partial=None):
        if not picking_type_in:
            picking_type_in = self.picking_type_in_warehouse
        if not partial or (partial and not hasattr(self, "po")):
            po = Form(self.env["purchase.order"])
            po.partner_id = self.vendor
            po.picking_type_id = picking_type_in

            with po.order_line.new() as po_line:
                po_line.product_id = self.product_1
                po_line.product_qty = self.qty_po_p1
                po_line.price_unit = self.price_p1

            with po.order_line.new() as po_line:
                po_line.product_id = self.product_2
                po_line.product_qty = self.qty_po_p2
                po_line.price_unit = self.price_p2

            po = po.save()
            po.button_confirm()
        else:
            po = self.po
        self.po = po
        return po

    def validate_picking(self, partial=None, vals=False):
        self.picking = self.po.picking_ids.filtered(lambda pick: pick.state != "done")
        self.writeOnPicking(vals)
        qty_po_p1 = self.qty_po_p1 if not partial else self.qty_po_p1 / 2
        qty_po_p2 = self.qty_po_p2 if not partial else self.qty_po_p2 / 2
        for move_line in self.picking.move_line_ids:
            if move_line.product_id == self.product_1:
                move_line.write({"qty_done": qty_po_p1})
            if move_line.product_id == self.product_2:
                move_line.write({"qty_done": qty_po_p2})

        self.picking.button_validate()
        self.picking._action_done()
        _logger.info("Receptie facuta")
        return self.picking

    def create_reception_progress_invoice(
        self, diff_p1=0, diff_p2=0, quant_p1=0, quant_p2=0
    ):
        rec_invoice = self.po.action_create_reception_in_progress_invoice()
        invoice = Form(self.env["account.move"].browse(rec_invoice.get("res_id")))
        invoice.invoice_date = fields.Date.today()
        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.quantity += quant_p1
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(1) as line_form:
            line_form.quantity += quant_p2
            line_form.price_unit += diff_p2
        invoice = invoice.save()
        invoice.action_post()
        self.invoice = invoice
        _logger.info("Factura introdusa")

    def test_nir_with_reception_in_progress(self):
        """
        Achizitie in curs
        """
        self.create_po()
        self.create_reception_progress_invoice()

        self.check_account_valuation(self.val_p1_i, self.val_p2_i, self.acc_327)

        self.check_account_valuation(0, 0)
        self.check_stock_valuation(0, 0)

        self.validate_picking()
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # soldul lui 327 trebuie sa fie zero
        self.check_account_valuation(0, 0, self.acc_327)

    def test_nir_with_reception_in_progress_invoices_warning(self):
        """
        Achizitie in curs, eroare validare picking, mai multe facturi
        """
        self.create_po()
        self.create_reception_progress_invoice()

        self.check_account_valuation(self.val_p1_i, self.val_p2_i, self.acc_327)

        self.check_account_valuation(0, 0)
        self.check_stock_valuation(0, 0)

        # Generare factura storno, cant receptionata 0, cantitate facturata 1
        self.po.action_create_invoice()
        invoice = self.po.invoice_ids.filtered(lambda p: p.state == "draft")
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()

        self.check_account_valuation(0, 0, self.acc_327)

        self.check_account_valuation(0, 0)
        self.check_stock_valuation(0, 0)

        with self.assertRaises(ValidationError):
            self.validate_picking()
