# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests import Form, tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoRequired(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

    def check_invoice_edi_fields(self, invoice, vals):
        form = Form(invoice)
        if vals.get("fields"):
            for field, value in vals["fields"].items():
                if value:
                    self.assertTrue(getattr(invoice, field))
                else:
                    self.assertFalse(getattr(invoice, field))
        if vals.get("l10n_ro_edi_transaction"):
            for attr, value in vals["l10n_ro_edi_transaction"].items():
                self.assertTrue(
                    form._get_modifier("l10n_ro_edi_transaction", attr) == value
                )
        if vals.get("l10n_ro_edi_download"):
            for attr, value in vals["l10n_ro_edi_download"].items():
                self.assertTrue(
                    form._get_modifier("l10n_ro_edi_download", attr) == value
                )

    def get_fields_and_view_vals(self, value1, value2):
        vals = {
            "fields": {
                "l10n_ro_edi_transaction": value1,
                "l10n_ro_show_edi_fields": value1,
                "l10n_ro_edi_fields_readonly": value1,
            },
            "l10n_ro_edi_transaction": {
                "invisible": value2,
                "readonly": value1,
            },
            "l10n_ro_edi_download": {
                "invisible": value2,
                "readonly": value1,
            },
        }
        return vals

    def get_fields_and_view_purchase_vals(self, value1, value2):
        vals = self.get_fields_and_view_vals(value1, value2)
        vals["fields"]["l10n_ro_show_edi_fields"] = True
        return vals

    def check_invoice_fields_invoice_sent(self, invoice):
        vals = self.get_fields_and_view_vals(False, True)
        invoice.action_post()
        self.check_invoice_edi_fields(invoice, vals)
        invoice.with_context(
            test_data=self.get_file("upload_success.xml")
        ).action_process_edi_web_services()
        vals = self.get_fields_and_view_vals(True, False)
        self.check_invoice_edi_fields(invoice, vals)

    def test_sale_invoice_fields(self):
        self.check_invoice_fields_invoice_sent(self.invoice)

    def test_sale_refund_fields(self):
        self.check_invoice_fields_invoice_sent(self.credit_note)

    def test_purchase_invoice_autoinvoice_fields(self):
        self.check_invoice_fields_invoice_sent(self.invoice_in)

    def test_purchase_refund_autoinvoice_fields(self):
        self.check_invoice_fields_invoice_sent(self.credit_note_in)

    def test_purchase_invoice_fields(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": "2022-09-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    ),
                ],
            }
        )
        vals = self.get_fields_and_view_purchase_vals(False, False)
        self.check_invoice_edi_fields(invoice, vals)
        invoice.write(
            {
                "l10n_ro_edi_transaction": "test",
                "l10n_ro_edi_download": "test",
            }
        )
        invoice.action_post()
        vals = self.get_fields_and_view_purchase_vals(True, False)
        self.check_invoice_edi_fields(invoice, vals)
        invoice.button_draft()
        self.assertEqual(invoice.l10n_ro_edi_transaction, "test")
        self.assertEqual(invoice.l10n_ro_edi_download, "test")
        self.check_invoice_edi_fields(invoice, vals)
