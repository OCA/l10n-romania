# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from datetime import date, timedelta
from unittest.mock import patch

from odoo.modules.module import get_module_resource
from odoo.tests import tagged

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase


@tagged("post_install", "-at_install")
class TestMessageSPV(AccountEdiTestCommon, CronMixinCase):
    # test de creare mesaje preluate de la SPV

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

        # Set up ANAF configuration
        anaf_config = cls.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        anaf_scope = [
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
        if not anaf_config:
            anaf_config = cls.env["l10n.ro.account.anaf.sync"].create(
                {
                    "company_id": cls.env.company.id,
                    "client_id": "123",
                    "client_secret": "123",
                    "access_token": "123",
                    "client_token_valability": date.today() + timedelta(days=10),
                    "anaf_scope_ids": anaf_scope,
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
        anaf_messages = b"""%s""" % json.dumps(msg_dict).encode("utf-8")

        with patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.l10n_ro_account_anaf_sync_scope."
            "AccountANAFSyncScope._l10n_ro_einvoice_call",
            return_value=(anaf_messages, 200),
        ):
            self.env.company.l10n_ro_download_message_spv()

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

        test_file = get_module_resource(
            "l10n_ro_account_edi_ubl", "tests", "invoice.zip"
        )
        anaf_messages = open(test_file, mode="rb").read()
        with patch(
            "odoo.addons.l10n_ro_account_edi_ubl.models.l10n_ro_account_anaf_sync_scope."
            "AccountANAFSyncScope._l10n_ro_einvoice_call",
            return_value=(anaf_messages, 200),
        ):
            message_spv.download_from_spv()
            message_spv.get_invoice_from_move()
            message_spv.create_invoice()
