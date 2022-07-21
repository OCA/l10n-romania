# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestStockCommon

# Generare note contabile la achizitie


@tagged("post_install", "-at_install")
class TestStockPurchase(TestStockCommon):
    def test_nir_with_invoice_standard(self):

        self.env.company.romanian_accounting = False

        self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

    def test_nir_with_invoice(self):
        """
        Receptie produse in depozit in baza facturii
         - in stoc valoarea de achiztie
         - in contabilitate valoarea de achiztie
         - in diferente de pret zero
         - in TVA neexigibilă zero
        """
        self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

    def test_nir_with_invoice_location_valuation(self):
        """
        Receptie produse in locatie cu alta evaluare in baza facturii
         - in stoc valoarea de achiztie
         - in contabilitate valoarea de achiztie
         - in diferente de pret zero
         - in TVA neexigibilă zero

        """

        self.set_warehouse_as_mp()

        self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        # se genereaza NC stoc la stoc
        # todo: cum o fi corect
        # self.check_account_valuation(0, 0)

        self.create_invoice()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(
            self.val_p1_i, self.val_p2_i, self.account_valuation_mp
        )

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

    def test_nir_with_invoice_and_diff(self):
        """
        Receptie produse in baza facturii cu inregistrare diferente dintre
        comanda de achizitie si factura
        Diferentele trebuie sa fie inregitrate in contul de stoc
            - in stoc valoarea de achiztie din factura
            - in contabilitate valoarea de achiztie din factura
            - in diferente de pret zero
            - in TVA neexigibilă zero
        """
        self.create_po()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice(self.diff_p1, self.diff_p2)

        # in stocul  are valoarea cu diferenta de pret inregistrata
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)
