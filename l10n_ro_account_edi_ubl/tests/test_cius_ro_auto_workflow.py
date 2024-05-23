# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from unittest.mock import patch

import freezegun

from odoo import fields
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from odoo.tests import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoAutoWorkflow(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

    # Helper method to prepare an invoice and simulate the step 1 of the CIUS workflow.
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

    # Test case for the successful processing of documents in step 1 of the CIUS workflow.
    def test_process_documents_web_services_step1_ok(self):
        self.prepare_invoice_sent_step1()

    # Test case for the cron job that processes documents in step 1 of the CIUS workflow.
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

    # Test case for the error handling in step 1 of the CIUS workflow.
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

    # Test case for the constraint handling in step 1 of the CIUS workflow.
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

    # Test case for the successful processing of documents in step 2 of the CIUS workflow.
    def test_process_documents_web_services_step2_ok(self):
        self.prepare_invoice_sent_step1()

    # Test case for the different scenarios of processing documents in step 2
    # of the CIUS workflow.
    def test_process_document_web_services_step2_not_ok(self):
        self.prepare_invoice_sent_step1()
        cases = [
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
                self.get_file("stare_mesaj_not_ok.xml"),
                "to_send",
                "The invoice was not validated by ANAF.",
                "error",
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

    # Helper method to test the processing of documents in step 2 of the CIUS workflow.
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

    def test_step2_not_ok_anaf_error(self):
        self.prepare_invoice_sent_step1()
        not_ok_content = self.get_file("stare_mesaj_not_ok.xml")
        anaf_error_zipfile = self.get_zip_file("3828.zip")

        def _l10n_ro_einvoice_call(self, func, params, data=None, method="POST"):
            if func == "/descarcare":
                return anaf_error_zipfile, 200
            else:
                return not_ok_content, 200

        with patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.l10n_ro_account_anaf_sync_scope."
            "AccountANAFSyncScope._l10n_ro_einvoice_call",
            _l10n_ro_einvoice_call,
        ):
            self.invoice.action_process_edi_web_services()
            self.check_invoice_documents(
                self.invoice,
                "to_send",
                "<p>Erori validare ANAF:<br>E: validari globale\n eroare regula: R6.1: CIF-ul vanzatorului nu figureaza in baza de date:6443019833<br></p>",  # noqa
                "error",
            )

    def test_download_invoice(self):
        data = self.invoice_zip
        self.invoice.invoice_line_ids = False
        self.invoice.l10n_ro_edi_download = "1234"
        self.invoice.with_context(test_data=data).l10n_ro_download_zip_anaf()
        with self.assertRaises(UserError):
            self.invoice.with_context(test_data=data).l10n_ro_download_zip_anaf()

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
                self.env.company._l10n_ro_get_anaf_efactura_messages(
                    filters={"tip": "FACTURA PRIMITA"}
                ),
                expected_msg,
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
