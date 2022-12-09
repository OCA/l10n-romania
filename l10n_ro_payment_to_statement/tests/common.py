# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.account.tests.test_account_payment_register import (
    TestAccountPaymentRegister,
)


class TestPaymenttoStatement(TestAccountPaymentRegister):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)
        cls.env.company.l10n_ro_accounting = True
        cls.partner_a = cls.env["res.partner"].create({"name": "test"})
        cash_journals = cls.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", cls.env.company.id)]
        )
        for journal in cash_journals:
            journal.l10n_ro_update_cash_vals()
