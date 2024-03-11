# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import json
import logging
import time
from datetime import date, timedelta
from unittest.mock import patch

import freezegun

from odoo import fields
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from odoo.tests import tagged

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestAccountEdiUbl(AccountEdiTestCommon, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)
        cls.env.company.l10n_ro_accounting = True

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
        if "street_name" in cls.env.company._fields:
            cls.env.company.write(
                {
                    "street_name": "Str. Ciprian Porumbescu Nr. 12",
                    "street": "Str. Ciprian Porumbescu Nr. 12",
                }
            )

        cls.bank = cls.env["res.partner.bank"].create(
            {
                "acc_type": "iban",
                "partner_id": cls.env.company.partner_id.id,
                "bank_id": cls.env.ref("l10n_ro.res_bank_37").id,
                "acc_number": "RO75TREZ0615069XXX001573",
            }
        )

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
                "l10n_ro_e_invoice": True,
                "l10n_ro_is_government_institution": False,
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

        cls.partner.l10n_ro_is_government_institution = True

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
        invoice_values = {
            "move_type": "out_invoice",
            "name": "FBRAO2092",
            "partner_id": cls.partner.id,
            "invoice_date": fields.Date.from_string("2022-09-01"),
            "date": fields.Date.from_string("2022-09-01"),
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
        cls.invoice = cls.env["account.move"].create(invoice_values)
        cls.invoice.journal_id.edi_format_ids = [
            (6, 0, cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro").ids)
        ]
        invoice_values.update(
            {
                "move_type": "out_refund",
                "name": "FBRAO2093",
            }
        )
        cls.credit_note = cls.env["account.move"].create(invoice_values)

        test_file = get_module_resource(
            "l10n_ro_account_edi_ubl", "tests", "invoice.zip"
        )
        cls.invoice_zip = open(test_file, mode="rb").read()

        anaf_config = cls.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        if not anaf_config:
            anaf_config = cls.env["l10n.ro.account.anaf.sync"].create(
                {
                    "company_id": cls.env.company.id,
                    "client_id": "123",
                    "client_secret": "123",
                    "access_token": "123",
                    "client_token_valability": date.today() + timedelta(days=10),
                    "anaf_scope_ids": [
                        (
                            0,
                            0,
                            {
                                "scope": "e-factura",
                                "state": "test",
                                "anaf_sync_test_url": "https://api.anaf.ro/test/FCTEL/rest",
                            },
                        )
                    ],
                }
            )
            anaf_config = cls.env.company._l10n_ro_get_anaf_sync(scope="e-factura")

    def get_file(self, filename):
        test_file = get_module_resource("l10n_ro_account_edi_ubl", "tests", filename)
        return open(test_file).read().encode("utf-8")

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
            self.assertTrue(
                any(error in message for message in invoice.message_ids.mapped("body"))
            )
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

    def test_account_invoice_edi_ubl(self):
        self.invoice.action_post()
        invoice_xml = self.invoice.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(self.get_file("invoice.xml"))
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_account_credit_note_edi_ubl(self):
        self.credit_note.action_post()
        invoice_xml = self.credit_note.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(self.get_file("credit_note.xml"))
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_account_credit_note_with_option_edi_ubl(self):
        self.credit_note.action_post()
        self.env.company.l10n_ro_credit_note_einvoice = True
        invoice_xml = self.credit_note.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(
            self.get_file("credit_note_option.xml")
        )
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def prepare_invoice_sent_step1(self):
        self.invoice.action_post()

        # procesare step 1 - succes
        self.invoice.with_context(
            test_data=self.get_file("upload_success.xml")
        ).action_process_edi_web_services()
        self.check_invoice_documents(
            self.invoice,
            "to_send",
            "<p>The invoice was sent to ANAF, awaiting validation.</p>",
            "info",
        )

    def test_process_documents_web_services_step1_ok(self):
        self.prepare_invoice_sent_step1()

    @freezegun.freeze_time("2022-09-04")
    def test_process_documents_web_services_step1_cron(self):
        anaf_config = self.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        anaf_config.anaf_sync_id.access_token = "test"
        self.invoice.action_post()

        self.env.company.l10n_ro_edi_residence = 3
        edi_documents = self.env["account.edi.document"].search(
            [
                ("state", "in", ("to_send", "to_cancel")),
                ("move_id.state", "=", "posted"),
            ]
        )
        edi_documents._process_documents_web_services(job_count=10)
        self.check_invoice_documents(
            self.invoice,
            "to_send",
            "<p>Access Error</p>",
            "warning",
        )

    def test_process_documents_web_services_step1_error(self):
        self.invoice.action_post()

        # procesare step 1 - eroare
        self.invoice.with_context(
            test_data=self.get_file("upload_standard_invalid.xml")
        ).action_process_edi_web_services()
        self.check_invoice_documents(
            self.invoice,
            "to_send",
            "<p>Valorile acceptate pentru parametrul standard sunt UBL, CII sau RASP</p>",
            "error",
        )

    def test_process_documents_web_services_step1_constraint(self):
        self.invoice.partner_id.state_id = False
        self.invoice.action_post()

        # procesare step 1 - eroare
        self.invoice.action_process_edi_web_services()
        self.check_invoice_documents(
            self.invoice,
            "to_send",
            "<p>{\"The field 'State' is required on SCOALA GIMNAZIALA COMUNA FOENI.\"}</p>",
            "warning",
        )

    def test_print_pdf_error(self):
        self.env.company.l10n_ro_edi_cius_embed_pdf = True
        self.invoice.action_post()
        self.invoice.partner_id.state_id = False

        # Print the invoice to append AdditionalDocumentReference.
        self.env["ir.actions.report"]._render_qweb_pdf(
            "account.account_invoices_without_payment", [self.invoice.id]
        )
        # generare fisier xml - eroare
        self.invoice.action_process_edi_web_services()
        self.check_invoice_documents(
            self.invoice,
            "to_send",
            "<p>{\"The field 'State' is required on SCOALA GIMNAZIALA COMUNA FOENI.\"}</p>",
            "warning",
        )

    def test_get_invoice_edi_content_error(self):
        self.env.company.l10n_ro_edi_cius_embed_pdf = True
        self.invoice.action_post()
        self.invoice.partner_id.state_id = False

        # Compute edi document with error, should be b''
        edi_doc = self.invoice.edi_document_ids
        edi_doc._compute_edi_content()
        self.assertEqual(edi_doc.edi_content, b"")

        # generare fisier xml - eroare
        self.check_invoice_documents(
            self.invoice,
            "to_send",
            "<p>{\"The field 'State' is required on SCOALA GIMNAZIALA COMUNA FOENI.\"}</p>",
            "warning",
        )

    def test_process_documents_web_services_step2_ok(self):
        self.prepare_invoice_sent_step1()

    def test_process_document_web_services_step2_not_ok(self):
        self.prepare_invoice_sent_step1()
        cases = [
            (
                self.get_file("stare_mesaj_not_ok.xml"),
                "to_send",
                "The invoice was not validated by ANAF.",
                "warning",
            ),
            (
                self.get_file("stare_mesaj_in_prelucrare.xml"),
                "to_send",
                "The invoice is in processing at ANAF.",
                "info",
            ),
            (
                self.get_file("stare_mesaj_limita_apeluri.xml"),
                "to_send",
                "<p>S-au facut deja 20 descarcari de mesaj in cursul zilei</p>",
                "warning",
            ),
            (
                self.get_file("stare_mesaj_xml_erori.xml"),
                "to_send",
                "XML with errors not taken over by the system",
                "error",
            ),
            (
                self.get_file("stare_mesaj_drept_id_incarcare.xml"),
                "to_send",
                "<p>Nu aveti dreptul de inteorgare pentru id_incarcare= 18</p>",
                "error",
            ),
            (
                self.get_file("stare_mesaj_lipsa_drepturi.xml"),
                "to_send",
                "<p>Nu exista niciun CIF petru care sa aveti drept</p>",
                "error",
            ),
            (
                self.get_file("stare_mesaj_index_invalid.xml"),
                "to_send",
                "<p>Id_incarcare introdus= aaa nu este un numar intreg</p>",
                "error",
            ),
            (
                self.get_file("stare_mesaj_factura_inexistenta.xml"),
                "to_send",
                "<p>Nu exista factura cu id_incarcare=</p>",
                "error",
            ),
        ]
        for check_case in cases:
            self.test_step2_not_ok(check_case)

    def test_step2_not_ok(self, check_case=False):
        if check_case:
            if check_case[3] == "error":
                self.invoice.edi_document_ids.write(
                    {"state": "to_send", "blocking_level": False, "error": False}
                )
            self.invoice.with_context(
                test_data=check_case[0]
            ).action_process_edi_web_services()
            self.check_invoice_documents(
                self.invoice, check_case[1], check_case[2], check_case[3]
            )

    def test_download_invoice(self):
        data = self.invoice_zip
        self.invoice.invoice_line_ids = False
        self.invoice.l10n_ro_edi_download = "1234"
        self.invoice.with_context(test_data=data).l10n_ro_download_zip_anaf()
        with self.assertRaises(UserError):
            self.invoice.with_context(test_data=data).l10n_ro_download_zip_anaf()

    def test_edi_cius_is_required(self):
        cius_format = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
        self.assertTrue(cius_format._is_required_for_invoice(self.invoice))
        self.invoice.partner_id.is_company = False
        self.assertFalse(cius_format._is_required_for_invoice(self.invoice))
        self.invoice.partner_id.is_company = True
        self.invoice.partner_id.country_id = False
        self.assertFalse(cius_format._is_required_for_invoice(self.invoice))

    def test_l10n_ro_get_anaf_efactura_messages(self):
        self.env.company.vat = "RO23685159"
        anaf_config = self.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        anaf_config.anaf_sync_id.access_token = "test"
        msg_dict = {
            "mesaje": [
                {
                    "data_creare": "202312120940",
                    "cif": "23685159",
                    "id_solicitare": "5004552043",
                    "detalii": "Factura cu id_incarcare=5004552043 emisa de "
                    "cif_emitent=8486152 pentru"
                    "cif_beneficiar=23685159",
                    "tip": "FACTURA PRIMITA",
                    "id": "3006372781",
                }
            ],
            "serial": "1234AA456",
            "cui": "8000000000",
            "titlu": "Lista Mesaje disponibile din ultimele 1 zile",
        }
        anaf_messages = b"""%s""" % json.dumps(msg_dict).encode("utf-8")
        expected_msg = [
            {
                "data_creare": "202312120940",
                "cif": "23685159",
                "id_solicitare": "5004552043",
                "detalii": "Factura cu id_incarcare=5004552043 emisa de "
                "cif_emitent=8486152 pentru"
                "cif_beneficiar=23685159",
                "tip": "FACTURA PRIMITA",
                "id": "3006372781",
            }
        ]
        with patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.l10n_ro_account_anaf_sync_scope."
            "AccountANAFSyncScope._l10n_ro_einvoice_call",
            return_value=(anaf_messages, 200),
        ):
            self.assertEqual(
                self.env.company._l10n_ro_get_anaf_efactura_messages(), expected_msg
            )

    def test_l10n_ro_create_anaf_efactura(self):
        anaf_config = self.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        anaf_config.anaf_sync_id.access_token = "test"
        self.env.company.l10n_ro_download_einvoices = True
        self.env.company.partner_id.write(
            {
                "vat": "RO34581625",
                "name": "AGROAMAT COM SRL",
                "phone": False,
                "email": False,
            }
        )
        self.env["res.partner"].create(
            {
                "name": "TOTAL SECURITY S.A.",
                "vat": "RO8486152",
                "country_id": self.env.ref("base.ro").id,
            }
        )
        messages = [
            {
                "data_creare": "202312120940",
                "cif": "34581625",
                "id_solicitare": "5004879752",
                "detalii": "Factura cu id_incarcare=5004879752 emisa de "
                "cif_emitent=8486152 pentru "
                "cif_beneficiar=34581625",
                "tip": "FACTURA PRIMITA",
                "id": "3006850898",
            }
        ]

        signed_zip_file = open(
            get_module_resource("l10n_ro_account_edi_ubl", "tests", "5004879752.zip"),
            mode="rb",
        ).read()
        with patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.res_company.ResCompany"
            "._l10n_ro_get_anaf_efactura_messages",
            return_value=messages,
        ), patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.l10n_ro_account_anaf_sync_scope."
            "AccountANAFSyncScope._l10n_ro_einvoice_call",
            return_value=(signed_zip_file, 200),
        ):
            self.env.company._l10n_ro_create_anaf_efactura()
            invoice = self.env["account.move"].search(
                [("l10n_ro_edi_download", "=", "3006850898")]
            )
            self.assertEqual(len(invoice), 1)
            self.assertEqual(invoice.l10n_ro_edi_download, "3006850898")
            self.assertEqual(invoice.l10n_ro_edi_transaction, "5004879752")
            self.assertEqual(invoice.move_type, "in_invoice")
            self.assertEqual(invoice.partner_id.vat, "RO8486152")

            self.assertEqual(invoice.ref, "INV/2023/00029")
            self.assertEqual(invoice.payment_reference, "INV/2023/00029")
            self.assertEqual(invoice.currency_id.name, "RON")
            self.assertEqual(
                invoice.invoice_date, fields.Date.from_string("2023-12-16")
            )
            self.assertEqual(
                invoice.invoice_date_due, fields.Date.from_string("2023-12-16")
            )
            self.assertAlmostEqual(invoice.amount_untaxed, 1000.0)
            self.assertAlmostEqual(invoice.amount_tax, 190.0)
            self.assertAlmostEqual(invoice.amount_total, 1190.0)
            self.assertAlmostEqual(invoice.amount_residual, 1190.0)
            self.assertEqual(invoice.invoice_line_ids[0].name, "test")
            self.assertAlmostEqual(invoice.invoice_line_ids[0].quantity, 1)
            self.assertAlmostEqual(invoice.invoice_line_ids[0].price_unit, 1000.0)
            self.assertAlmostEqual(invoice.invoice_line_ids[0].balance, 1000.0)
