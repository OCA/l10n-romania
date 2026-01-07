# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommonPriceDiff

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockSale(TestStockCommonPriceDiff):
    def test_sale_and_invoice_price_difference(self):
        """
                Receptie produse in baza facturii cu inregistrare diferente dintre
        comanda de achizitie si factura
        Vanzare si facturare
             - initial in stoc si contabilitate este valoarea din achizitie ajustata
             cu diferentele
             - dupa vanzare valoarea stocului trebuie sa scada cu valoarea stocului
             vandut, tinand cont si de diferentele inregistrate la intrare
             - valoarea din stoc trebuie sa fie egala cu valoarea din contabilitate
             - in contul de venituri trebuie sa fie inregistrata valoarea de vanzare
        """

        #  intrare in stoc
        self.create_po()
        self.create_invoice(self.diff_p1, self.diff_p2)

        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        # iesire din stoc prin vanzare
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        val_stock_p1 = round(self.val_p1_f - self.val_stock_out_so_p1_diff, 2)
        val_stock_p2 = round(self.val_p2_f - self.val_stock_out_so_p2_diff, 2)

        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        self.create_sale_invoice()

        _logger.info("Verificare valoare ramas in stoc")
        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        _logger.info("Verifcare valoare vanduta")
        self.check_account_valuation(
            -self.val_so_p1, -self.val_so_p2, self.account_income
        )
