# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import tagged

from .common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockPurchaseDozen(TestStockCommon):
    def test_dozen_uom_nir_with_invoice_and_no_diff(self):
        """
        Receptie produs product_1 in unitate de masura Dozen,
        qty = 1, PO uom = Dozen (12 Units), price_unit = 12

        Factura qty = 1, UOM Dozen, price_unit = 12 (doar pt product_1)
        => Nu exista diferenta
        """
        self._setup_dozen()
        self.create_po(receive_products=False)
        qty_done_p1 = self.product_1.uom_po_id._compute_quantity(
            self.qty_po_p1, self.product_1.uom_id
        )
        qty_done_p2 = self.product_2.uom_po_id._compute_quantity(
            self.qty_po_p2, self.product_2.uom_id
        )

        self.po_receive_products(qty_done_p1, qty_done_p2)

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice(0.0, 0.0)

        # in stocul  are valoarea fara diferenta
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

    def test_dozen_uom_nir_with_invoice_and_diff_prod_1(self):
        """
        Receptie produs product_1 in unitate de masura Dozen,
        qty = 1, PO uom = Dozen (12 Units), price_unit = 12

        Factura qty = 1, UOM Dozen, price_unit = 13 (doar pt product_1)
        => Diferenta de pret 1 leu
        """
        self._setup_dozen()
        self.create_po(receive_products=False)
        qty_done_p1 = self.product_1.uom_po_id._compute_quantity(
            self.qty_po_p1, self.product_1.uom_id
        )
        qty_done_p2 = self.product_2.uom_po_id._compute_quantity(
            self.qty_po_p2, self.product_2.uom_id
        )

        self.po_receive_products(qty_done_p1, qty_done_p2)

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice(self.diff_p1, 0.0)

        # in stocul  are valoarea cu diferenta de pret inregistrata
        self.check_stock_valuation(self.val_p1_f, self.val_p2_i)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_f, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)
