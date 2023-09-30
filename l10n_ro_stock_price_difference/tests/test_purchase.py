# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import tagged

from .common import TestStockCommonPriceDiff


@tagged("post_install", "-at_install")
class TestStockPurchase(TestStockCommonPriceDiff):
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
        # in stoc e valoarea cu diferenta de pret inregistrata
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are acceasi valoare
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(0, 0)

    def test_nir_with_notice_invoice_and_diff(self):
        """
        Receptie produse pe baza de aviz si inregistare ulterioara a facturii
        cu inregistrare diferente dintre comanda de achizitie si factura
         - Diferentele trebuie sa fie inregitrate in contul de diferente de stoc

         De fortat sa foloseasca contul de stoc la diferente de pret

        """
        self.create_po(vals={"l10n_ro_notice": True})

        # in stoc produsele sunt la valoarea de achizitie
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        self.create_invoice(self.diff_p1, self.diff_p2)

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
        inregistare ulterioara a facturii cu diferente
        dintre comanda de achizitie si factura

        """
        self.create_po(vals={"l10n_ro_notice": True})

        # in stoc produsele sunt la valoarea de achizitie
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # Creeza consum: 2 bucati la pret 50
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )
        self.transfer(location_id, location_dest_id, self.product_1)
        self.transfer(location_id, location_dest_id, self.product_2)

        # Validare factura pret 51 pt product1, 49 pt product2
        self.create_invoice(self.diff_p1, self.diff_p2)

        # in stoc produsele sunt la valoarea din factura - consum
        self.check_stock_valuation(self.val_p1_f - 102, self.val_p2_f - 98)

        # in contabilitate stocul are valoarea din factura - consum
        self.check_account_valuation(self.val_p1_f - 102, self.val_p2_f - 98)

        # verificare inregistrare diferenta de pret
        self.check_account_diff(
            self.val_p1_f - self.val_p1_i, self.val_p2_f - self.val_p2_i
        )

        # soldul lui 408 trebuie sa fie zero
        self.check_account_valuation(0, 0, self.stock_picking_payable_account_id)

    def test_nir_with_partial_receipt_one_invoice_and_diff(self):
        """
        Receptie produse partial si 1 factura cu diferenta de pret

        """
        self.create_po(partial=True)

        # in stoc produsele sunt la valoarea de achizitie 0
        self.check_stock_valuation(self.val_p1_i / 2, self.val_p2_i / 2)

        self.check_account_valuation(0, 0)

        self.create_po(partial=True)

        # in stoc produsele sunt la valoarea de achizitie 0
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)

        self.check_account_valuation(0, 0)

        # Validare factura pret 51 pt product1, 49 pt product2
        self.create_invoice(self.diff_p1, self.diff_p2)

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

    def test_nir_with_partial_receipt_two_invoice_and_diff(self):
        """
        Receptie produse partial si 2 facturi cu diferenta de pret

        """
        self.create_po(partial=True)

        # in stoc produsele sunt la valoarea de achizitie 0
        self.check_stock_valuation(self.val_p1_i / 2, self.val_p2_i / 2)

        self.check_account_valuation(0, 0)

        # Validare factura pret 51 pt product1, 49 pt product2
        self.create_invoice(self.diff_p1, self.diff_p2)

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f / 2, self.val_p2_f / 2)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f / 2, self.val_p2_f / 2)

        self.create_po(partial=True)

        # in stoc produsele sunt la valoarea de achizitie 0
        self.check_stock_valuation(self.val_p1_i + 5, self.val_p2_i - 5)

        self.check_account_valuation(self.val_p1_f / 2, self.val_p2_f / 2)

        # Validare factura pret 51 pt product1, 49 pt product2
        self.create_invoice(self.diff_p1, self.diff_p2)

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

    def test_nir_with_partial_receipt_one_invoice_total_and_diff(self):
        """
        Receptie produse partial si 1 factura cu diferenta de pret
        pe toata cantitatea

        """
        self.create_po(partial=True)

        # in stoc produsele sunt la valoarea de achizitie 0
        self.check_stock_valuation(self.val_p1_i / 2, self.val_p2_i / 2)

        self.check_account_valuation(0, 0)

        # Validare factura pret 51 pt product1, 49 pt product2
        self.create_invoice(self.diff_p1, self.diff_p2, 5, 5)

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f / 2, self.val_p2_f / 2)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        self.create_po(partial=True)

        # in stoc produsele sunt la valoarea din factura minus diferenta pe receptia partiala
        # self.check_stock_valuation(self.val_p1_f - 5, self.val_p2_f + 5)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        self.invoice.button_draft()
        self.invoice.with_context(l10n_ro_approved_price_difference=True).action_post()

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)
