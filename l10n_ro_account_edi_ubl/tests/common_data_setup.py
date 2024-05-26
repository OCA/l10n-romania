# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import time
from datetime import date, timedelta

from odoo import fields
from odoo.modules.module import get_module_resource
from odoo.tests import tagged

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class CiusRoTestSetup(AccountEdiTestCommon, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        # Set up chart of accounts
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)
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
            }
        )
        cls.env.company.partner_id.l10n_ro_vat_subjected = (True,)
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
            cls.partner.write({"street_name": "Nr. 383", "street": "Foeni Nr. 383"})

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
                "l10n_ro_nc_code": "25050000",
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

        # Set up tax 0
        cls.tax_0 = cls.env["account.tax"].create(
            {
                "name": "tax_0",
                "amount_type": "percent",
                "amount": 0,
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

        cls.supplier_partner = cls.env["res.partner"].create(
            {
                "name": "NEXTERP ROMANIA SRL",
                "ref": "NEXTERP ROMANIA SRL",
                "vat": "RO39187746",
                "country_id": cls.env.ref("base.ro").id,
                "l10n_ro_vat_subjected": True,
                "street": "Foeni Nr. 383",
                "city": "Foeni",
                "state_id": cls.country_state.id,
                "zip": "307175",
                "phone": "0256413409",
                "is_company": True,
            }
        )
        if "street_name" in cls.partner._fields:
            cls.partner.write({"street_name": "Nr. 383", "street": "Foeni Nr. 383"})

        invoice_values_tax_0 = {
            "move_type": "out_invoice",
            "name": "FBRAO2092",
            "partner_id": cls.partner.id,
            "invoice_date": fields.Date.from_string("2022-09-01"),
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
                        "tax_ids": [(6, 0, cls.tax_0.ids)],
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
                        "tax_ids": [(6, 0, cls.tax_0.ids)],
                    },
                ),
            ],
        }

        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        # invoice tax 19%
        cls.invoice = cls.env["account.move"].create(invoice_values)
        cls.invoice.journal_id.edi_format_ids = [(6, 0, cls.edi_cius_format.ids)]
        # invoice tax 0%
        cls.invoice_tax_0 = cls.env["account.move"].create(invoice_values_tax_0)
        cls.invoice_tax_0.journal_id.edi_format_ids = [(6, 0, cls.edi_cius_format.ids)]

        # Update the invoice_values and create a credit_note
        invoice_values.update(
            {
                "move_type": "out_refund",
                "name": "FBRAO2093",
            }
        )
        invoice_values_tax_0.update(
            {
                "move_type": "out_refund",
                "name": "FBRAO2093",
            }
        )
        # credit note tax 19%
        cls.credit_note = cls.env["account.move"].create(invoice_values)
        # credit note tax 0%
        cls.credit_note_tax_0 = cls.env["account.move"].create(invoice_values_tax_0)

        # Set up test file
        test_file = get_module_resource(
            "l10n_ro_account_edi_ubl", "tests", "invoice.zip"
        )
        cls.invoice_zip = open(test_file, mode="rb").read()

        # Set up ANAF configuration
        anaf_config = cls.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        if not anaf_config:
            efact_scope = [
                (
                    0,
                    0,
                    {
                        "scope": "e-factura",
                        "state": "test",
                        "anaf_sync_production_url": "https://api.anaf.ro/prod/FCTEL/rest",
                        "anaf_sync_test_url": "https://api.anaf.ro/test/FCTEL/rest",
                    },
                )
            ]
            anaf_config = cls.env["l10n.ro.account.anaf.sync"].create(
                {
                    "company_id": cls.env.company.id,
                    "client_id": "123",
                    "client_secret": "123",
                    "access_token": "123",
                    "client_token_valability": date.today() + timedelta(days=10),
                    "anaf_scope_ids": efact_scope,
                }
            )
            anaf_config = cls.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        cls.anaf_config = anaf_config

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

        cls.journal_CIUS.edi_format_ids = [(6, 0, cls.edi_cius_format.ids)]

        # Update the invoice_values and create a invoice_in
        invoice_values.update(
            {
                "move_type": "in_invoice",
                "name": "FBRAO2094",
                "journal_id": cls.journal_CIUS.id,
                "partner_id": cls.supplier_partner.id,
            }
        )
        invoice_values_tax_0.update(
            {
                "move_type": "in_invoice",
                "name": "FBRAO2094",
                "journal_id": cls.journal_CIUS.id,
            }
        )
        # credit note tax 19%
        cls.invoice_in = cls.env["account.move"].create(invoice_values)
        # credit note tax 0%
        cls.invoice_in_tax_0 = cls.env["account.move"].create(invoice_values_tax_0)

        # Update the invoice_values and create a credit_note_in
        invoice_values.update(
            {
                "move_type": "in_refund",
                "name": "FBRAO2095",
            }
        )
        invoice_values_tax_0.update(
            {
                "move_type": "in_refund",
                "name": "FBRAO2095",
            }
        )
        # credit note tax 19%
        cls.credit_note_in = cls.env["account.move"].create(invoice_values)
        # credit note tax 0%
        cls.credit_note_in_tax_0 = cls.env["account.move"].create(invoice_values_tax_0)

    # Utility methods
    def get_file(self, filename):
        # Get the content of a test file
        test_file = get_module_resource("l10n_ro_account_edi_ubl", "tests", filename)
        return open(test_file).read().encode("utf-8")

    # Utility methods
    def get_zip_file(self, filename):
        # Get the content of a test file
        bytes_content = b""
        test_file = get_module_resource("l10n_ro_account_edi_ubl", "tests", filename)
        with open(test_file, "rb") as file_data:
            bytes_content = file_data.read()
        return bytes_content

    def check_invoice_documents(
        self, invoice, state="to_send", error=False, blocking_level=False
    ):
        sleep_time = 0
        while not invoice.edi_state and sleep_time < 30:
            time.sleep(1)
            sleep_time += 1
        self.assertEqual(len(invoice.edi_document_ids), 1)
        self.assertEqual(invoice.edi_state, state)
        self.assertEqual(invoice.edi_document_ids.state, state)
        if error:
            self.assertTrue(invoice.edi_document_ids.error)
            self.assertIn(error, invoice.edi_document_ids.error)
            # self.assertTrue(
            #     any(error in message for message in invoice.message_ids.mapped("body"))
            # )
        if blocking_level:
            self.assertEqual(invoice.edi_document_ids.blocking_level, blocking_level)
            if blocking_level == "error":
                self.assertTrue(invoice.activity_ids)
                self.assertTrue(
                    any(
                        error in activity
                        for activity in invoice.activity_ids.mapped("note")
                    )
                )
