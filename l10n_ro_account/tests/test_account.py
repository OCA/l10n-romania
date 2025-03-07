# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccount(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)

    def setUp(self):
        super(TestAccount, self).setUp()
        self.env.company.l10n_ro_accounting = True

        self.account = self.env["account.account"].create(
            {
                "code": "301001",
                "name": "Test account",
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
