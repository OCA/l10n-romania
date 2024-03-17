# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests.common import TransactionCase


class TestAccountANAFSync(TransactionCase):
    def setUp(self):
        super(TestAccountANAFSync, self).setUp()
        self.test_company = self.env["res.company"].create({"name": "Test Sync"})
        self.sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.test_company.id,
                "client_id": "123",
                "client_secret": "123",
            }
        )

    def test_anaf_api(self):
        self.sync.test_anaf_api()

    def test_revoke_access_token(self):
        self.sync.write({"access_token": "123"})
        self.sync.revoke_access_token()

    def test_get_access_token(self):
        self.sync.get_token_from_anaf_website()
