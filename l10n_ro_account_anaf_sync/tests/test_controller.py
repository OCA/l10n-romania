# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields
from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestAnafSyncControllers(HttpCase):
    def setUp(self):
        super(TestAnafSyncControllers, self).setUp()
        self.test_company = self.env["res.company"].create({"name": "Test Sync"})
        self.sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.test_company.id,
                "client_id": "123",
                "client_secret": "123",
                "access_token": "123",
            }
        )

    def test_redirect_anaf(self):
        self.authenticate("demo", "demo")
        response = self.url_open(
            "/l10n_ro_account_anaf_sync/redirect_anaf/%s" % self.sync.id
        )
        self.assertTrue(response.status_code)

    def test_anaf_oauth(self):
        self.sync.write({"last_request_datetime": fields.Datetime.now()})
        response = self.url_open(
            "/l10n_ro_account_anaf_sync/anaf_oauth/%s" % self.sync.id,
            data={"code": "123"},
        )
        self.assertEqual(response.status_code, 200)
