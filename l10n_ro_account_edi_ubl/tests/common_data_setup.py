# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import time
from datetime import date, timedelta
from unittest.mock import Mock, patch

import requests

from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import file_path

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class CiusRoTestSetup(TestUBLCommon, CronMixinCase):
    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.l10n_ro_accounting = True

        # Set up company details
        cls.currency = cls.env["res.currency"].search([("name", "=", "RON")])
        cls.country_state = cls.env.ref("base.RO_TM")
        cls.env.company.write({"vat": "RO30834857"})
        cls.env.company.write(
            {
                "vat": "RO30834857",
                "name": "FOREST AND BIOMASS ROMÂNIA S.A.",
                "country_id": cls.env.ref("base.ro").id,
                "currency_id": cls.currency.id,
                "street": "Str. Ciprian Porumbescu Nr. 12",
                "street2": "Zona Nr.3, Etaj 1",
                "city": "Timișoara",
                "state_id": cls.country_state.id,
                "zip": "300011",
                "phone": "0356179038",
                "invoice_is_ubl_cii": True,
                "email": "admin@admin.com",
            }
        )
        if "street_name" in cls.env.company._fields:
            cls.env.company.write(
                {
                    "street_name": "Str. Ciprian Porumbescu Nr. 12",
                    "street": "Str. Ciprian Porumbescu Nr. 12",
                }
            )

        # Set up bank details
        cls.bank = cls.env["res.partner.bank"].create(
            {
                "acc_type": "iban",
                "partner_id": cls.env.company.partner_id.id,
                "bank_id": cls.env.ref("l10n_ro.res_bank_37").id,
                "acc_number": "RO75TREZ0615069XXX001573",
            }
        )

        # Set up partner details
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "SCOALA GIMNAZIALA COMUNA FOENI",
                "ref": "SCOALA GIMNAZIALA COMUNA FOENI",
                "vat": "29152430",
                "country_id": cls.env.ref("base.ro").id,
                "l10n_ro_vat_subjected": False,
                "street": "Foeni Nr. 383",
                "city": "Foeni",
                "state_id": cls.country_state.id,
                "zip": "307175",
                "phone": "0256413409",
                "is_company": True,
            }
        )
        if "street_name" in cls.partner._fields:
            cls.partner.write(
                {
                    "street_name": "Foeni",
                    "street_number": "Nr. 383",
                    "street": "Foeni Nr. 383",
                }
            )

        # Set up products
        uom_id = cls.env.ref("uom.product_uom_unit").id
        cls.product_a = cls.env["product.product"].create(
            {
                "name": "Bec P21/5W",
                "default_code": "00000623",
                "uom_id": uom_id,
                "uom_po_id": uom_id,
            }
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Bec P21/10W",
                "default_code": "00000624",
                "uom_id": uom_id,
                "uom_po_id": uom_id,
            }
        )

        # Set up tax
        cls.tax_19 = cls.env["account.tax"].create(
            {
                "name": "tax_19",
                "amount_type": "percent",
                "amount": 19,
                "type_tax_use": "sale",
                "sequence": 19,
                "company_id": cls.env.company.id,
            }
        )

        # Set up invoice
        invoice_values = {
            "move_type": "out_invoice",
            "name": "FBRAO2092",
            "partner_id": cls.partner.id,
            "invoice_date": fields.Date.from_string("2022-09-01"),
            "invoice_date_due": fields.Date.from_string("2022-09-01"),
            "currency_id": cls.currency.id,
            "partner_bank_id": cls.bank.id,
            "invoice_line_ids": [
                (
                    0,
                    None,
                    {
                        "product_id": cls.product_a.id,
                        "name": "[00000623] Bec P21/5W",
                        "quantity": 5,
                        "price_unit": 1000.00,
                        "tax_ids": [(6, 0, cls.tax_19.ids)],
                    },
                ),
                (
                    0,
                    None,
                    {
                        "product_id": cls.product_b.id,
                        "name": "[00000624] Bec P21/10W",
                        "quantity": 5,
                        "price_unit": 1000.00,
                        "tax_ids": [(6, 0, cls.tax_19.ids)],
                    },
                ),
            ],
        }
        journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        invoice_values["journal_id"] = journal.id
        cls.invoice = cls.env["account.move"].create(invoice_values)

        # Update the invoice_values and create a credit_note
        invoice_values.update(
            {
                "move_type": "out_refund",
                "name": "FBRAO2093",
            }
        )
        cls.credit_note = cls.env["account.move"].create(invoice_values)

        # Set up test file
        test_file = file_path("l10n_ro_account_edi_ubl/tests/invoice.zip")
        cls.invoice_zip = open(test_file, mode="rb").read()
        invoice_xml_file = file_path("l10n_ro_account_edi_ubl/tests/invoice.xml")
        cls.invoice_xml = open(invoice_xml_file, mode="rb").read()

        # Set up ANAF configuration
        cls.env.company.write(
            {
                "l10n_ro_edi_access_token": "123",
                "l10n_ro_edi_client_id": "123",
                "l10n_ro_edi_client_secret": "123",
                "l10n_ro_edi_refresh_token": "123",
                "l10n_ro_edi_access_expiry_date": date.today() + timedelta(days=10),
            }
        )

        # Create account.journal record
        cls.journal_CIUS = cls.env["account.journal"].create(
            {
                "name": "Test Journal CIUS",
                "type": "purchase",
                "default_account_id": cls.company_data["default_account_expense"].id,
                "code": "TJ-CIUS",
                "l10n_ro_sequence_type": "autoinv2",
                "l10n_ro_partner_id": cls.partner.id,
            }
        )

        # Update the invoice_values and create a invoice_in
        invoice_values.update(
            {
                "move_type": "in_invoice",
                "name": "FBRAO2094",
                "journal_id": cls.journal_CIUS.id,
            }
        )
        cls.invoice_in = cls.env["account.move"].create(invoice_values)

        # Update the invoice_values and create a credit_note_in
        invoice_values.update(
            {
                "move_type": "in_refund",
                "name": "FBRAO2095",
            }
        )
        cls.credit_note_in = cls.env["account.move"].create(invoice_values)

    # Utility methods
    def get_file(self, filename):
        # Get the content of a test file
        test_file = file_path("l10n_ro_account_edi_ubl/tests/" + filename)
        return open(test_file).read().encode("utf-8")

    # Utility methods
    def get_zip_file(self, filename):
        # Get the content of a test file
        bytes_content = b""
        test_file = file_path("l10n_ro_account_edi_ubl/tests/" + filename)
        with open(test_file, "rb") as file_data:
            bytes_content = file_data.read()
        return bytes_content

    def check_invoice_documents(
        self,
        invoice,
        state="invoice_sending",
        error=False,
        check_activity=False,
        user_id=False,
        has_edi_document=True,
    ):
        sleep_time = 0
        while not invoice.l10n_ro_edi_state and sleep_time < 30:
            time.sleep(1)
            sleep_time += 1
        if has_edi_document:
            self.assertEqual(invoice.l10n_ro_edi_state, state)
            self.assertTrue(invoice.l10n_ro_edi_document_ids)
            self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
            self.assertTrue(invoice.l10n_ro_edi_document_ids.attachment_id)
            self.assertEqual(invoice.l10n_ro_edi_document_ids.state, state)
            if error:
                self.assertTrue(invoice.l10n_ro_edi_document_ids.message)
                self.assertIn(error, invoice.l10n_ro_edi_document_ids.message)
        else:
            self.assertFalse(invoice.l10n_ro_edi_state)
        if (
            not check_activity
            and invoice.l10n_ro_edi_document_ids.state == "invoice_sending_failed"
        ):
            check_activity = True
        if check_activity:
            domain = [("res_id", "=", invoice.id), ("res_model", "=", "account.move")]
            if user_id:
                domain.append(("user_id", "=", user_id))
            activity = self.env["mail.activity"].search(domain)
            self.assertTrue(activity)
            self.assertTrue(
                any(
                    error in msg
                    for msg in activity.mapped("note")
                    + invoice.sudo().activity_ids.mapped("summary")
                )
            )

    def get_attachment(self, move):
        if not move.ubl_cii_xml_id:
            xml_data, _build_errors = self.env[
                "account.edi.xml.ubl_ro"
            ]._export_invoice(move)
        else:
            xml_data = move.ubl_cii_xml_id.raw
        edi_doc = move._l10n_ro_edi_create_document_invoice_sending("123", xml_data)
        attachment = edi_doc.attachment_id
        self.assertTrue(attachment)
        return attachment

    def _mocked_successful_empty_get_response(self, *args, **kwargs):
        """This mock is used when requesting documents, such as labels."""
        response = Mock()
        response.status_code = 200
        response.content = ""
        return response
    
    def _mocked_successful_empty_post_response(self, *args, **kwargs):
        """This mock is used when requesting documents, such as labels."""
        response = Mock()
        response.status_code = 200
        response.content = ""
        return response
    
    # Helper method to prepare an invoice and simulate the step 1 of the CIUS workflow.
    def prepare_invoice_sent_step1(self):
        self.invoice.action_post()

        # procesare step 1 - succes
        self.l10n_ro_edi_send_test_invoice(self.invoice, "3828")
        self.check_invoice_documents(
            self.invoice,
            "invoice_sending",
        )
    
    def l10n_ro_edi_send_test_invoice(self, invoice, key_loading):
        xml_data = self.get_attachment(invoice).datas.decode("utf-8")
        with patch.object(
            requests, "post", self._mocked_successful_empty_post_response
        ), patch(
            "odoo.addons.l10n_ro_efactura.models.ciusro_document."
            "L10nRoEdiDocument._request_ciusro_send_invoice",
            return_value={'key_loading': key_loading},
        ):
            invoice._l10n_ro_edi_send_invoice(xml_data)