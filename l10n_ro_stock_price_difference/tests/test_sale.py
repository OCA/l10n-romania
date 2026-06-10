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

    def test_nir_sale_then_invoice_with_price_diff(self):
        """
        Achizitie produs stocabil cu categorie FIFO. Receptie in stoc, vanzare
        produse, si abia dupa vanzare se inregistreaza factura cu diferenta de pret.
        Se verifica ca valoarea de iesire (COGS) reflecta pretul complet,
        incluzand diferenta de pret (pret PO + diferenta de pret).
        """
        diff_p1 = 10  # 10 lei diferenta de pret per unitate la product_1 (FIFO)
        diff_p2 = 0

        # Intrare in stoc - la receptie directa nu se face nota contabila
        self.create_po()
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(0, 0)

        # Iesire din stoc prin vanzare (inainte de factura cu diferenta de pret)
        self.create_so()

        # Dupa livrare: SVL la costul initial din PO
        val_svl_after_so_p1 = round(self.val_p1_i - self.qty_so_p1 * self.price_p1, 2)
        val_svl_after_so_p2 = round(self.val_p2_i - self.qty_so_p2 * self.price_p2, 2)
        self.check_stock_valuation(val_svl_after_so_p1, val_svl_after_so_p2)

        # Inregistrare factura cu diferenta de pret DUPA vanzare
        self.create_invoice(diff_p1, diff_p2)

        # Valori finale asteptate
        val_p1_f = round(self.qty_po_p1 * (self.price_p1 + diff_p1), 2)  # 10*60=600
        val_p2_f = round(self.qty_po_p2 * (self.price_p2 + diff_p2), 2)  # 10*50=500

        # COGS: qty_so unitati la (pret_PO + diferenta_pret)
        val_cogs_p1 = round(self.qty_so_p1 * (self.price_p1 + diff_p1), 2)  # 5*60=300
        val_cogs_p2 = round(self.qty_so_p2 * (self.price_p2 + diff_p2), 2)  # 5*50=250

        # Stoc ramas: (qty_po - qty_so) unitati la (pret_PO + diferenta_pret)
        val_stock_p1 = val_p1_f - val_cogs_p1  # 600-300=300
        val_stock_p2 = val_p2_f - val_cogs_p2  # 500-250=250

        _logger.info("Verificare SVL stoc ramas")
        self.check_stock_valuation(val_stock_p1, val_stock_p2)

        _logger.info("Verificare contabilitate stoc ramas")
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        _logger.info("Verificare COGS: iesirea la pretul din factura (PO + diferenta)")
        self.check_account_valuation(val_cogs_p1, val_cogs_p2, self.account_expense)
