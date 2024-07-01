# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from odoo.tests import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoAutoWorkflowDownload(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

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
