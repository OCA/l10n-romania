# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests.common import TransactionCase


class TestAccount(TransactionCase):
    def setUp(self):
        super(TestAccount, self).setUp()
        self.env.company.l10n_ro_accounting = True

        self.account = self.env["account.account"].create(
            {
                "code": "301001",
                "name": "Test account",
                "user_type_id": self.env.ref(
                    "account.data_account_type_current_liabilities"
                ).id,
            }
        )

    def test_internal_to_external(self):
        code = self.account.internal_to_external()
        self.assertEqual(code, "301.1")

    def test_external_code_to_internal(self):
        account_id = self.env["account.account"].external_code_to_internal("301.1")
        self.assertEqual(account_id, self.account.id)

    def test_name_get(self):
        name = self.account.name_get()
        self.assertEqual(name, [(self.account.id, "301.1 Test account")])
