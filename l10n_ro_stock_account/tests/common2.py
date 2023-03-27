# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import fields
from odoo.tests import Form, tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCommon2(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockCommon2, cls).setUpClass()
        cls.price_p1_2 = 60.0
        cls.price_p2_2 = 60.0
        cls.val_p1_i = round(cls.qty_po_p1 * (cls.price_p1 + cls.price_p1_2), 2)
        cls.val_p2_i = round(cls.qty_po_p2 * (cls.price_p2 + cls.price_p2_2), 2)
        cls.val_p1_f = round(
            cls.qty_po_p1 * (cls.price_p1 + cls.price_p1_2 + 2 * cls.diff_p1), 2
        )
        cls.val_p2_f = round(
            cls.qty_po_p2 * (cls.price_p2 + cls.price_p2_2 + 2 * cls.diff_p2), 2
        )
        cls.val_stock_out_so_p1 = round(
            cls.qty_po_p1 * cls.price_p1 + cls.qty_po_p1 / 2 * cls.price_p1_2, 2
        )
        cls.val_stock_out_so_p2 = round(
            cls.qty_po_p2 * cls.price_p2 + cls.qty_po_p2 / 2 * cls.price_p2_2, 2
        )

    def create_po(
        self, picking_type_in=None, partial=None, vals=False, validate_picking=True
    ):

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
                po_line.product_id = self.product_1
                po_line.product_qty = self.qty_po_p1
                po_line.price_unit = self.price_p1_2

            with po.order_line.new() as po_line:
                po_line.product_id = self.product_2
                po_line.product_qty = self.qty_po_p2
                po_line.price_unit = self.price_p2

            with po.order_line.new() as po_line:
                po_line.product_id = self.product_2
                po_line.product_qty = self.qty_po_p2
                po_line.price_unit = self.price_p2_2

            po = po.save()
            po.button_confirm()
        else:
            po = self.po

        if validate_picking:
            self.picking = po.picking_ids.filtered(lambda pick: pick.state != "done")
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

        self.po = po
        return po

    def create_invoice(
        self, diff_p1=0, diff_p2=0, quant_p1=0, quant_p2=0, auto_post=True
    ):
        invoice = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice",
                default_invoice_date=fields.Date.today(),
                active_model="accoun.move",
            )
        )
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po

        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.quantity += quant_p1
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(1) as line_form:
            line_form.quantity += quant_p1
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(2) as line_form:
            line_form.quantity += quant_p2
            line_form.price_unit += diff_p2
        with invoice.invoice_line_ids.edit(3) as line_form:
            line_form.quantity += quant_p2
            line_form.price_unit += diff_p2

        invoice = invoice.save()
        if invoice.amount_total < 0:
            invoice.action_switch_invoice_into_refund_credit_note()
        if quant_p1 or quant_p2 or diff_p1 or diff_p2:
            invoice = invoice.with_context(l10n_ro_approved_price_difference=True)
        if auto_post:
            invoice.action_post()

        self.invoice = invoice
        _logger.debug("Factura introdusa")
