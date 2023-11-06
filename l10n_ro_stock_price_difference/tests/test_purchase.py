# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import Form, tagged

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

    def test_purchase_in_eur_with_invoice_and_diff_in_eur(self):
        self.create_po_default(
            {
                "currency": self.currency_eur,
            }
        )

        ron_value1 = self.qty_po_p1 * self.price_p1 * self.rate
        ron_value2 = self.qty_po_p2 * self.price_p2 * self.rate

        ron_value_f1 = self.qty_po_p1 * (self.price_p1 + self.diff_p1) * self.rate
        ron_value_f2 = self.qty_po_p2 * (self.price_p2 + self.diff_p2) * self.rate

        self.check_stock_valuation(ron_value1, ron_value2)
        # in contabilitate trebuie sa fie zero pentru ca la receptie nu
        # trebuie generata nota cantabila
        self.check_account_valuation(0, 0)

        self.create_invoice(self.diff_p1, self.diff_p2)
        # in stocul  are valoarea cu diferenta de pret inregistrata

        self.check_stock_valuation(ron_value_f1, ron_value_f2)

        # in contabilitate stocul este inregistrat cu diferentele de pret
        self.check_account_valuation(ron_value_f1, ron_value_f2)

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
        self.check_stock_valuation(self.val_p1_f - 5, self.val_p2_f + 5)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

        self.invoice.button_draft()
        self.invoice.with_context(l10n_ro_approved_price_difference=True).action_post()

        # in stoc produsele sunt la valoarea din factura
        self.check_stock_valuation(self.val_p1_f, self.val_p2_f)

        # in contabilitate stocul are valoarea din factura
        self.check_account_valuation(self.val_p1_f, self.val_p2_f)

    def test_2_nir_and_1_invoice_with_price_diff(self):
        "Doua receptii de pe doua comenzi de achzitie cu o singura factura cu diferenta de pret"
        self.create_po_default(
            {
                "lines": [
                    {
                        "product": self.product_1,
                        "qty": 2,
                        "price": 5,
                    },
                    {
                        "product": self.product_2,
                        "qty": 2,
                        "price": 5,
                    },
                ]
            }
        )
        po1 = self.po
        self.create_po_default(
            {
                "lines": [
                    {
                        "product": self.product_1,
                        "qty": 2,
                        "price": 5,
                    },
                    {
                        "product": self.product_2,
                        "qty": 2,
                        "price": 5,
                    },
                ]
            }
        )
        po2 = self.po

        self.check_stock_valuation(20, 20)
        self.check_account_valuation(0, 0)

        invoice_form = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice",
                default_invoice_date=fields.Date.today(),
                active_model="account.move",
            )
        )
        invoice_form.partner_id = self.vendor
        invoice_form.purchase_id = po1

        invoice = invoice_form.save()

        invoice_form = Form(invoice)
        invoice_form.purchase_id = po2
        invoice = invoice_form.save()

        invoice_form = Form(invoice)
        for line in range(0, 4):
            with invoice_form.invoice_line_ids.edit(line) as line_form:
                line_form.price_unit += 1

        invoice = invoice_form.save()

        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()

        self.check_stock_valuation(24, 24)
        self.check_account_valuation(24, 24)
