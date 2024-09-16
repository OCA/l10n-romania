# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from unittest.mock import Mock, patch

import requests

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.misc import file_path

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoAutoWorkflowDownload(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def _mocked_successful_empty_get_response(self, *args, **kwargs):
        """This mock is used when requesting documents, such as labels."""
        response = Mock()
        response.status_code = 200
        response.content = ""
        return response

    def test_download_invoice(self):
        data = self.invoice_zip
        self.invoice.invoice_line_ids = False
        self.invoice.l10n_ro_edi_download = "1234"
        with self.assertRaises(UserError):
            with patch.object(
                requests, "get", self._mocked_successful_empty_get_response
            ):
                self.invoice.with_context(test_data=data).l10n_ro_download_zip_anaf()

    def test_l10n_ro_get_anaf_efactura_messages(self):
        self.env.company.vat = "RO23685159"
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
        with patch.object(
            requests, "get", self._mocked_successful_empty_get_response
        ), patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.res_company."
            "ResCompany._l10n_ro_get_anaf_efactura_messages",
            return_value=anaf_messages,
        ):
            response = json.loads(
                self.env.company._l10n_ro_get_anaf_efactura_messages(
                    filters={"filtru": "P"}
                )
            )
            messages = response.get("mesaje")
            self.assertEqual(messages, expected_msg)

    def test_l10n_ro_create_anaf_efactura(self):
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
        anaf_messages = [
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
            file_path("l10n_ro_account_edi_ubl/tests/5004879752.zip"), mode="rb"
        ).read()
        xml_file = open(
            file_path("l10n_ro_account_edi_ubl/tests/5004879752.xml"), mode="rb"
        ).read()
        with patch.object(
            requests, "get", self._mocked_successful_empty_get_response
        ), patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.res_company."
            "ResCompany._l10n_ro_get_anaf_efactura_messages",
            return_value=anaf_messages,
        ), patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.ciusro_document."
            "L10nRoEdiDocument._request_ciusro_download_zipfile",
            return_value={
                "attachment_zip": signed_zip_file,
                "attachment_raw": xml_file,
            },
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
