# Copyright (C) 2024 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase


@tagged("post_install", "-at_install")
class TestMessageSPV(AccountEdiTestCommon, CronMixinCase):
    # test de creare mesaje preluate de la SPV

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()

        cls.mainpartner = cls.env.ref("base.main_partner")
        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True
        cls.env.company.l10n_ro_edi_access_token = "123"

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

        # # Set up ANAF configuration
        # anaf_config = cls.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        # anaf_scope = [
        #     (
        #         0,
        #         0,
        #         {
        #             "scope": "e-factura",
        #             "state": "test",
        #             "anaf_sync_production_url": "https://api.anaf.ro/prod/FCTEL/rest",
        #             "anaf_sync_test_url": "https://api.anaf.ro/test/FCTEL/rest",
        #         },
        #     )
        # ]
        # if not anaf_config:
        #     cls.env["l10n.ro.account.anaf.sync"].create(
        #         {
        #             "company_id": cls.env.company.id,
        #             "client_id": "123",
        #             "client_secret": "123",
        #             "access_token": "123",
        #             "client_token_valability": date.today() + timedelta(days=10),
        #             "anaf_scope_ids": anaf_scope,
        #         }
        #     )
