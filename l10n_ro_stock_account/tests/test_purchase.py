# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestStockCommon

# Generare note contabile la achizitie


@tagged("post_install", "-at_install")
class TestStockPurchase(TestStockCommon):
    def test_nir_with_invoice_standard(self):

        self.env.company.l10n_ro_accounting = False

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

    def test_two_nirs_average(self):
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "average"
        self.product_2.product_tmpl_id.categ_id.property_cost_method = "average"
        self.create_po()

        self.price_p1 = 60.0
        self.create_po()

        self.assertEqual(self.product_1.standard_price, 55)
        self.assertEqual(self.product_2.standard_price, 50)

    def test_nir_with_account_mp(self):
        self.product_1.product_tmpl_id.categ_id = self.category_mp
        self.product_2.product_tmpl_id.categ_id = self.category_mp

        self.create_po()

        self.check_stock_valuation(
            self.val_p1_i, self.val_p2_i, self.account_valuation_mp
        )

        self.check_account_valuation(0, 0, self.account_valuation_mp)

        self.create_invoice()

        self.check_stock_valuation(
            self.val_p1_i, self.val_p2_i, self.account_valuation_mp
        )

        self.check_account_valuation(
            self.val_p1_i, self.val_p2_i, self.account_valuation_mp
        )

        self.check_account_diff(0, 0)
