# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests.common import TransactionCase


class TestAccountANAFSync(TransactionCase):
    def setUp(self):
        super(TestAccountANAFSync, self).setUp()

    def test_anaf_api(self):
        sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "client_id": "123",
                "client_secret": "123",
                "access_token": "123",
            }
        )
        sync.test_anaf_api()

    def test_revoke_access_token(self):
        sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "client_id": "123",
                "client_secret": "123",
                "access_token": "123",
            }
        )
        sync.revoke_access_token()

    def test_get_access_token(self):
        sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.env.ref("base.main_company").id,
                "client_id": "123",
                "client_secret": "123",
            }
        )
        sync.get_token_from_anaf_website()
