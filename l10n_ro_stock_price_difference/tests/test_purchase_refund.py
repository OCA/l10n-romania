# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.tests import Form, tagged

from .common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockPurchaseRefund(TestStockCommon):
    def test_nir_with_invoice_and_refund_partial_no_difference(self):
        po = self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice(auto_post=False)

        pick = po.picking_ids
        self.make_return(pick, 10)

        stock_value_final_p1 = self.val_p1_i - round(10 * self.price_p1, 2)
        stock_value_final_p2 = self.val_p1_i - round(10 * self.price_p2, 2)
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
        self.make_return(pick, 20)

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

    def test_dozen_uom_nir_with_invoice_and_diff_and_partial_refund(self):
        """
        Receptie produs product_1 in unitate de masura Dozen,
        qty = 2, PO uom = Dozen (12 Units), price_unit = 12,
        se fac 2 receptii partiale, fiecare cu 12 Units

        Factura qty = 2, UOM Dozen, price_unit = 13 (doar pt product_1)
        => Diferenta de pret 1 leu

        apoi retur 1 Dozen
        => Diferenta de 1 leu
        """

        # setup
        self.product_1.uom_po_id = self.env.ref("uom.product_uom_dozen")
        self.qty_po_p1 = 2
        self.price_p1 = 12
        self.diff_p1 = 1

        self.product_2.uom_po_id = self.env.ref("uom.product_uom_dozen")
        self.qty_po_p2 = 2
        self.price_p2 = 12
        self.diff_p2 = 0

        self.val_p1_i = round(self.qty_po_p1 * self.price_p1, 2)
        self.val_p2_i = round(self.qty_po_p2 * self.price_p2, 2)
        self.val_p1_f = round(self.qty_po_p1 * (self.price_p1 + self.diff_p1), 2)
        self.val_p2_f = round(self.qty_po_p2 * (self.price_p2 + self.diff_p2), 2)

        self.create_po(receive_products=False)
        qty_done_p1 = self.product_1.uom_po_id._compute_quantity(
            self.qty_po_p1, self.product_1.uom_id
        )
        qty_done_p2 = self.product_2.uom_po_id._compute_quantity(
            self.qty_po_p2, self.product_2.uom_id
        )

        # se fac 2 receptii
        self.po_receive_products(qty_done_p1, qty_done_p2, partial=True)
        self.po_receive_products(qty_done_p1 / 2, qty_done_p2 / 2)

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.po.action_create_invoice()
        self.po.invoice_ids[-1].invoice_date = fields.Date.today()

        # ajustare price_unit sa fie 13 lei, deoarece din PO vine 12 lei
        invoice = Form(self.po.invoice_ids[-1])
        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit += self.diff_p1

        invoice = invoice.save()
        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()

        # in stocul  are valoarea cu diferenta de pret inregistrata pt product 1
        # diferenta de 1 leu se adauga la Remaining Value de la ultimul SVL receptionat
        # este important deoarece cand se va returna (mai jos), ultimul SVL receptionat
        # va avea Remaing Value = 0, deci se scade si diferenta de pret
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

        # Retur 12 Units = 1 Dozen
        pick = self.po.picking_ids[-1]
        self.make_return(pick, 12)

        # aici se scoate si diferenta
        stock_value_p1 = self.val_p1_i - round(1 * self.price_p1, 2)
        stock_value_final_p2 = self.val_p2_i - round(1 * self.price_p2, 2)

        self.check_stock_valuation(stock_value_p1, stock_value_final_p2)

        # create credit note
        # Credit note pentru 1 Dozen, la price_unit de 13 lei
        self.po.action_create_invoice()
        self.po.invoice_ids[-1].invoice_date = fields.Date.today()

        # ajustare price_unit sa fie 13 lei, deoarece din PO vine 12 lei
        invoice = Form(self.po.invoice_ids[-1])
        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 1
            line_form.price_unit += self.diff_p1

        invoice = invoice.save()
        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()

        # in stoc se mai face un SVL price difference
        stock_value_final_p1 = self.val_p1_f - round(
            1 * (self.price_p1 + self.diff_p1), 2
        )
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
