# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

import freezegun

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
        self.assertEqual(self.invoice.l10n_ro_edi_transaction, "3828")
        self.assertEqual(self.invoice.l10n_ro_edi_previous_transaction, "3828")
        self.invoice.button_draft()
        self.assertEqual(self.invoice.l10n_ro_edi_transaction, False)
        self.assertEqual(self.invoice.l10n_ro_edi_previous_transaction, "3828")
        self.prepare_invoice_sent_step1()
        self.assertEqual(self.invoice.l10n_ro_edi_transaction, "3828")
        self.assertEqual(self.invoice.l10n_ro_edi_previous_transaction, "3828")

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

    def test_step2_not_ok_anaf_error_users_activities(self):
        self.prepare_invoice_sent_step1()
        not_ok_content = self.get_file("stare_mesaj_not_ok.xml")
        anaf_error_zipfile = self.get_zip_file("3828.zip")
        users = self.env.ref("base.user_admin") + self.env.ref("base.user_demo")
        self.env.company.l10n_ro_edi_error_notify_users = users

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
            for user in users:
                self.check_invoice_documents(
                    self.invoice,
                    "to_send",
                    "<p>Erori validare ANAF:<br>E: validari globale\n eroare regula: R6.1: CIF-ul vanzatorului nu figureaza in baza de date:6443019833<br></p>",  # noqa
                    "error",
                    user_id=user.id,
                )
