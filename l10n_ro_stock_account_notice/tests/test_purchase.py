# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

# Generare note contabile la achizitie


@tagged("post_install", "-at_install")
class TestStockPurchase(TestStockCommon):

    def test_nir_with_notice_and_invoice(self):
        """
        Receptie produse pe baza de aviz si inregistare
        ulterioara a facturii
        """
        self.create_po(picking={'notice':True})

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # soldul lui 408 trebuie sa fie zero
        self.check_account_valuation(0, 0, self.stock_picking_payable_account_id)

    def test_nir_with_notice_invoice_and_diff(self):
        """
        Receptie produse pe baza de aviz si inregistare ulterioara a facturii
        cu inregistrare diferente dintre comanda de achizitie si factura
         - Diferentele trebuie sa fie inregitrate in contul de diferente de stoc

         De fortat sa foloseasca contul de stoc la diferente de pret

        """
        self.create_po(picking={'notice':True})

        # in stoc produsele sunt la valoarea de achizitie
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice(self.diff_p1, self.diff_p2)

        # # in stoc produsele sunt la valoarea de achizitie
        # self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        #
        # # in contabilitate stocul are acceasi valoare
        # self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(
            self.val_p1_f - self.val_p1_i, self.val_p2_f - self.val_p2_i
        )

        # soldul lui 408 trebuie sa fie zero
        self.check_account_valuation(0, 0, self.stock_picking_payable_account_id)

    def test_nir_with_notice_invoice_and_diff_after_consumption(self):
        """
        Receptie produse pe baza de aviz,
         consum partial din produsele receptionate,
         inregistare ulterioara a facturii  cu diferente
               dintre comanda de achizitie si factura

        """
        self.create_po(picking={'notice':True})

        # in stoc produsele sunt la valoarea de achizitie
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice(self.diff_p1, self.diff_p2)
