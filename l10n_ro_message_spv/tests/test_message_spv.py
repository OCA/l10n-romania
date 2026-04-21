# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools.misc import file_path

from .common import TestMessageSPV


@tagged("post_install", "-at_install")
class TestMessageSPV(TestMessageSPV):
    # test de creare mesaje preluate de la SPV

    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {
                "name": "Deltatech",
                "country_id": self.env.ref("base.ro").id,
                "vat": "RO20603502",
                "is_company": True,
            }
        )

    def test_download_messages(self):
        # test de descarcare a mesajelor de la SPV
        self.env.company.vat = "RO23685159"

        msg_dict = {
            "mesaje": [
                {
                    "data_creare": "202312120940",
                    "cif": "23685159",
                    "id_solicitare": "5004552043",
                    "detalii": "Factura cu id_incarcare=5004552043 emisa de cif_emitent=8486152 pentru cif_beneficiar=23685159",  # noqa
                    "tip": "FACTURA PRIMITA",
                    "id": "3006372781",
                }
            ],
            "serial": "1234AA456",
            "cui": "8000000000",
            "titlu": "Lista Mesaje disponibile din ultimele 1 zile",
        }
        anaf_messages = {"content": b"""%s""" % json.dumps(msg_dict).encode("utf-8")}

        with patch(
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            self.env.company._l10n_ro_download_message_spv()

    def test_download_from_spv(self):
        # test descarcare zip from SPV
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "cif": "8486152",
            }
        )

        file_invoice = file_path("l10n_ro_message_spv/tests/invoice.zip")
        anaf_messages = {"content": open(file_invoice, "rb").read()}
        with patch(
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            message_spv.download_from_spv()
        message_spv.get_invoice_from_move()
        message_spv.create_invoice()
        message_spv.show_invoice()

    def test_unlink_account_move(self):
        """Testează funcționalitatea de ștergere a
        facturilor care au mesaje SPV atașate"""
        # Creăm o factură și mesaje SPV atașate
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "cif": "8486152",
            }
        )

        # Creăm atașamente
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test_attachment",
                "type": "binary",
                "datas": b"dGVzdA==",  # "test" codificat în base64
            }
        )

        # Asociăm atașamentele cu mesajul SPV
        message_spv.write(
            {
                "attachment_id": attachment.id,
            }
        )

        # Creăm o factură și o asociem cu mesajul SPV
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        message_spv.write({"invoice_id": invoice.id})

        # Verificăm că mesajul SPV este asociat cu factura
        self.assertEqual(invoice.l10n_ro_message_spv_ids[0].id, message_spv.id)

        # Ștergem factura
        invoice.unlink()

        # Verificăm că atașamentul nu mai este asociat cu niciun model/înregistrare
        self.assertFalse(attachment.res_id)
        self.assertFalse(attachment.res_model)

    def test_edi_transaction_tracking(self):
        """Testează câmpurile de urmărire a tranzacțiilor EDI"""
        # Creăm o factură
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )

        # Setăm valorile pentru câmpurile de urmărire a tranzacțiilor
        transaction_id = "TR123456789"
        download_id = "DL987654321"

        invoice.write(
            {
                "l10n_ro_edi_transaction": transaction_id,
                "l10n_ro_edi_download": download_id,
            }
        )

        # Verificăm că valorile au fost setate corect
        self.assertEqual(invoice.l10n_ro_edi_transaction, transaction_id)
        self.assertEqual(invoice.l10n_ro_edi_download, download_id)

    def test_vendor_code_on_post(self):
        """Testează adăugarea codului de furnizor la postarea facturii"""
        # Creăm un produs
        product = self.env["product.product"].create(
            {
                "name": "Test Product",
            }
        )

        # Creăm o factură cu linie ce conține codul furnizorului

        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2023-12-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Test Line",
                            "quantity": 1,
                            "price_unit": 100,
                            "l10n_ro_vendor_code": "VEND001",
                        },
                    )
                ],
            }
        )

        # Postăm factura
        invoice.action_post()

        # Verificăm că s-a creat o informație de furnizor cu codul corect
        supplier_info = self.env["product.supplierinfo"].search(
            [
                ("partner_id", "=", self.vendor.id),
                ("product_id", "=", product.id),
            ]
        )

        self.assertTrue(supplier_info)
        self.assertEqual(supplier_info.product_code, "VEND001")

    def test_download_attempts_limit(self):
        """Testează limitarea la 3 încercări de descărcare și trecerea
        în starea de eroare"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_LIMIT",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
            }
        )

        # Simulăm un răspuns cu eroare de la ANAF
        error_response = {"error": "Limita de descărcări atinsă"}

        with patch(
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=error_response,
        ):
            # Prima încercare
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 1)
            self.assertEqual(message_spv.state, "draft")

            # A doua încercare
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 2)
            self.assertEqual(message_spv.state, "draft")

            # A treia încercare -> starea devine eroare
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 3)
            self.assertEqual(message_spv.state, "error")

    def test_download_attempts_daily_reset(self):
        """Testează resetarea încercărilor de descărcare la schimbarea zilei"""
        yesterday = fields.Date.today() - relativedelta(days=1)
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_RESET",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "download_attempts": 2,
                "last_download_date": yesterday,
            }
        )

        # Simulăm un răspuns cu eroare
        error_response = {"error": "Eroare temporară"}

        with patch(
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=error_response,
        ):
            # Descărcarea astăzi ar trebui să reseteze încercările la 1
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 1)
            self.assertEqual(message_spv.last_download_date, fields.Date.today())

    def test_multi_company_isolation(self):
        """Testează izolarea datelor între companii și check_company"""
        company_b = self.env["res.company"].create({"name": "Company B"})

        # Mesaj în Compania A (default)
        message_a = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_A",
                "company_id": self.env.company.id,
            }
        )

        # Atașament în Compania B
        attachment_b = self.env["ir.attachment"].create(
            {
                "name": "file_b",
                "company_id": company_b.id,
                "datas": b"dGVzdA==",
            }
        )

        # Încercarea de a lega atașamentul din Compania B la mesajul din Compania A
        # ar trebui să eșueze din cauza check_company=True
        # Folosim contextul de companie A și un utilizator care nu este super-user
        # pentru a forța verificările de companie (deși check_company ar trebui să
        # funcționeze oricum)
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user_isolation",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_multi_company").id,
                            self.env.ref("account.group_account_invoice").id,
                        ],
                    )
                ],
                "company_ids": [(6, 0, [self.env.company.id, company_b.id])],
                "company_id": self.env.company.id,
            }
        )
        with self.assertRaises(AccessError):
            message_a.with_user(user).with_context(
                allowed_company_ids=self.env.company.ids
            ).write({"attachment_id": attachment_b.id})

    def test_cron_error_persistence_with_rollback(self):
        """Testează dacă download_attempts este salvat de cron chiar
        și în caz de excepție Python (rollback)"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_ROLLBACK",
                "company_id": self.env.company.id,
                "state": "draft",
                "download_attempts": 0,
            }
        )

        # Forțăm o excepție în timpul download_from_spv pentru a
        # declanșa rollback-ul tranzacției interne
        with self.assertLogs(
            "odoo.addons.l10n_ro_message_spv.models.res_company", level="ERROR"
        ) as cm:
            with patch.object(
                type(self.env["l10n.ro.message.spv"]),
                "download_from_spv",
                side_effect=Exception("Crash!"),
            ):
                # Rulăm cron-ul (metoda din res.company)
                self.env.company.l10n_ro_download_zip_message_spv(limit=1)

            # Verificăm că eroarea a fost logată
            self.assertTrue(
                any("Eroare la descărcarea ZIP" in log for log in cm.output)
            )

        # Verificăm că, în ciuda crash-ului, cron-ul a salvat eroarea
        # și a incrementat încercările
        message_spv.invalidate_recordset()
        self.assertEqual(message_spv.state, "error")
        self.assertEqual(message_spv.download_attempts, 1)
        self.assertIn("Crash!", message_spv.error)
