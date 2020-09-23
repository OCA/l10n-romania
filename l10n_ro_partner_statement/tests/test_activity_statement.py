# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields
from odoo.tests.common import TransactionCase


class TestActivityStatement(TransactionCase):
    """ Tests for Activity Statement."""

    def setUp(self):
        super().setUp()

        self.res_users_model = self.env["res.users"]
        self.company = self.env.ref("base.main_company")
        self.company.external_report_layout_id = self.env.ref(
            "web.external_layout_standard"
        )
        self.partner1 = self.env["res.partner"].create({"name": "TEST partner 1"})
        self.partner2 = self.env["res.partner"].create({"name": "TEST partner 2"})

        self.g_account_user = self.env.ref("account.group_account_user")

        self.user = self._create_user("user_1", [self.g_account_user], self.company).id

        self.statement_model = self.env["report.partner_statement.activity_statement"]
        self.wiz = self.env["activity.statement.wizard"]
        self.report_name = "partner_statement.activity_statement"
        self.report_title = "Activity Statement"
        self.today = fields.Date.context_today(self.wiz)

    def _create_user(self, login, groups, company):
        group_ids = [group.id for group in groups]
        user = self.res_users_model.create(
            {
                "name": login,
                "login": login,
                "email": "example@yourcompany.com",
                "company_id": company.id,
                "company_ids": [(4, company.id)],
                "groups_id": [(6, 0, group_ids)],
            }
        )
        return user

    def test_customer_activity_statement(self):

        wiz_id = self.wiz.with_context(
            active_ids=[self.partner1.id, self.partner2.id]
        ).create({})

        wiz_id.aging_type = "months"
        wiz_id.show_aging_buckets = False
        wiz_id.show_debit_credit = True
        wiz_id.onchange_aging_type()
        wiz_id.button_export_pdf()

        data = wiz_id._prepare_statement()
        docids = data["partner_ids"]
        report = self.statement_model._get_report_values(docids, data)
        self.assertIsInstance(
            report, dict, "There was an error while compiling the report."
        )
        self.assertIn(
            "bucket_labels", report, "There was an error while compiling the report."
        )
