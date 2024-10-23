# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

import freezegun
import requests

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoAutoWorkflow(CiusRoTestSetup, TestAccountMoveSendCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    # Test case for the successful processing of documents in step 1
    # of the CIUS workflow.
    def test_process_documents_web_services_step1_ok(self):
        self.prepare_invoice_sent_step1()
        self.assertEqual(self.invoice.l10n_ro_edi_transaction, "3828")
        self.assertEqual(self.invoice.l10n_ro_edi_previous_transaction, "3828")
        self.invoice.button_draft()
        self.assertEqual(self.invoice.l10n_ro_edi_transaction, False)
        self.assertEqual(self.invoice.l10n_ro_edi_previous_transaction, "3828")
        self.prepare_invoice_sent_step1()
        self.assertEqual(self.invoice.l10n_ro_edi_transaction, "3828")
        self.assertEqual(self.invoice.l10n_ro_edi_previous_transaction, "3828")

    # Test case for the cron job that processes documents in step 1
    # of the CIUS workflow.
    @freezegun.freeze_time("2022-09-04")
    def test_process_documents_web_services_step1_cron(self):
        self.invoice.action_post()

        self.env.company.l10n_ro_edi_residence = 3
        edi_documents = self.env["l10n_ro_edi.document"].search(
            [
                ("state", "in", ("invoice_sending", "invoice_sending_failed")),
                ("invoice_id.state", "=", "posted"),
            ]
        )
        edi_documents._process_documents_web_services(job_count=10)
        self.check_invoice_documents(
            self.invoice,
            "invoice_sending",
            "<p>Access Error</p>",
        )

    # Test case for the error handling in step 1 of the CIUS workflow.
    def test_process_documents_web_services_step1_error(self):
        self.invoice.action_post()

        # procesare step 1 - eroare
        with patch.object(
            requests, "post", self._mocked_successful_empty_post_response
        ):
            self.invoice.with_context(
                test_data=self.get_file("upload_standard_invalid.xml"),
                force_report_rendering=True,
            )._generate_pdf_and_send_invoice(
                self.move_template, allow_fallback_pdf=False
            )
            self.check_invoice_documents(
                self.invoice,
                "invoice_sending",
                "<p>Valorile acceptate pentru parametrul standard sunt UBL,"
                " CII sau RASP</p>",
            )

    # Test case for the constraint handling in step 1 of the CIUS workflow.
    def test_process_documents_web_services_step1_constraint(self):
        self.invoice.partner_id.state_id = False
        self.invoice.action_post()
        with self.assertRaises(UserError):
            self.invoice.with_context(
                force_report_rendering=True
            )._generate_pdf_and_send_invoice(
                self.move_template, allow_fallback_pdf=False
            )

            # procesare step 1 - eroare
            self.check_invoice_documents(
                self.invoice,
                "invoice_sending",
                "<p>{\"The field 'State' is required on"
                ' SCOALA GIMNAZIALA COMUNA FOENI."}</p>',  # noqa
                has_edi_document=False,
            )

    # Test case for the successful processing of documents
    # in step 2 of the CIUS workflow.
    def test_process_documents_web_services_step2_ok(self):
        self.prepare_invoice_sent_step1()

    # Test case for the different scenarios of processing documents in step 2
    # of the CIUS workflow.
    def test_process_document_web_services_step2_not_ok(self):
        self.prepare_invoice_sent_step1()
        cases = [
            (
                self.get_file("stare_mesaj_in_prelucrare.xml"),
                "invoice_sending",
                "The invoice is in processing at ANAF.",
            ),
            (
                self.get_file("stare_mesaj_limita_apeluri.xml"),
                "invoice_sending",
                "<p>S-au facut deja 20 descarcari de mesaj in cursul zilei</p>",
            ),
            (
                self.get_file("stare_mesaj_not_ok.xml"),
                "invoice_sending",
                "The invoice was not validated by ANAF.",
            ),
            (
                self.get_file("stare_mesaj_xml_erori.xml"),
                "invoice_sending",
                "XML with errors not taken over by the system",
            ),
            (
                self.get_file("stare_mesaj_drept_id_incarcare.xml"),
                "invoice_sending",
                "<p>Nu aveti dreptul de inteorgare pentru id_incarcare= 18</p>",
            ),
            (
                self.get_file("stare_mesaj_lipsa_drepturi.xml"),
                "invoice_sending",
                "<p>Nu exista niciun CIF petru care sa aveti drept</p>",
            ),
            (
                self.get_file("stare_mesaj_index_invalid.xml"),
                "invoice_sending",
                "<p>Id_incarcare introdus= aaa nu este un numar intreg</p>",
            ),
            (
                self.get_file("stare_mesaj_factura_inexistenta.xml"),
                "invoice_sending",
                "<p>Nu exista factura cu id_incarcare=</p>",
            ),
        ]
        for check_case in cases:
            self.test_step2_not_ok(check_case)

    # Helper method to test the processing of documents in step 2 of the CIUS workflow.
    def test_step2_not_ok(self, check_case=False):
        if check_case:
            self.invoice.with_context(
                force_report_rendering=True, test_data=check_case[0]
            )._generate_pdf_and_send_invoice(
                self.move_template, allow_fallback_pdf=False
            )
            self.check_invoice_documents(self.invoice, check_case[1], check_case[2])

    def test_step2_not_ok_anaf_error(self):
        self.prepare_invoice_sent_step1()
        not_ok_content = self.get_file("stare_mesaj_not_ok.xml")
        anaf_error_zipfile = self.get_zip_file("3828.zip")

        def _request_ciusro_download_answer(self, company, key_download, session):
            if func == "/descarcare":
                return {
                    "attachemnt_raw": anaf_error_zipfile,
                    "key_signature": "test",
                    "key_certificate": "test",
                }
            else:
                return {
                    "attachemnt_raw": not_ok_content,
                    "key_signature": "test",
                    "key_certificate": "test",
                }

        with patch.object(requests, "get", self._mocked_successful_empty_get_response):
            with patch(
                "odoo.addons.l10n_ro_efactura.models.ciusro_document."
                "L10nRoEdiDocument._request_ciusro_download_answer",
                _request_ciusro_download_answer,
            ):
                self.invoice._l10n_ro_edi_fetch_invoice_sending_documents()
                self.check_invoice_documents(
                    self.invoice,
                    "invoice_sending",
                    "<p>Erori validare ANAF:<br>E: validari globale\n eroare regula: R6.1: CIF-ul vanzatorului nu figureaza in baza de date:6443019833<br></p>",  # noqa
                )

    def test_step2_not_ok_anaf_error_users_activities(self):
        self.prepare_invoice_sent_step1()
        not_ok_content = self.get_file("stare_mesaj_not_ok.xml")
        anaf_error_zipfile = self.get_zip_file("3828.zip")
        users = self.env.ref("base.user_admin") + self.env.ref("base.user_demo")
        self.env.company.l10n_ro_edi_error_notify_users = users

        def _request_ciusro_download_answer(self, company, key_download, session):
            if func == "/descarcare":
                return {
                    "attachemnt_raw": anaf_error_zipfile,
                    "key_signature": "test",
                    "key_certificate": "test",
                }
            else:
                return {
                    "attachemnt_raw": not_ok_content,
                    "key_signature": "test",
                    "key_certificate": "test",
                }

        with patch.object(requests, "get", self._mocked_successful_empty_get_response):
            with patch(
                "odoo.addons.l10n_ro_efactura.models.ciusro_document."
                "L10nRoEdiDocument._request_ciusro_download_answer",
                _request_ciusro_download_answer,
            ):
                self.invoice._l10n_ro_edi_fetch_invoice_sending_documents()
                for user in users:
                    self.check_invoice_documents(
                        self.invoice,
                        "invoice_sending",
                        "<p>Erori validare ANAF:<br>E: validari globale\n eroare regula: R6.1: CIF-ul vanzatorului nu figureaza in baza de date:6443019833<br></p>",  # noqa
                        user_id=user.id,
                    )
