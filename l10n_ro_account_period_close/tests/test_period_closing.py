# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import time

from dateutil.relativedelta import relativedelta

from odoo import fields, tools
from odoo.modules.module import get_resource_path
from odoo.tests.common import TransactionCase


class TestCurrencyReevaluation(TransactionCase):
    def setUp(self):
        super(TestCurrencyReevaluation, self).setUp()
        ref = self.env.ref
        self.per_close_model = self.env["account.period.closing"]
        self.wiz_close_model = self.env["account.period.closing.wizard"]
        # load account_minimal_test.xml file for chart of account in configuration
        tools.convert_file(
            self.cr,
            "l10n_ro_account_period_close",
            get_resource_path("account", "test", "account_minimal_test.xml"),
            {},
            "init",
            False,
            "test",
            self.registry._assertion_report,
        )

        self.misc_journal = ref("l10n_ro_account_period_close.miscellaneous_journal")
        self.debit_acc = ref("l10n_ro_account_period_close.current_liabilities")
        self.credit_acc = ref("l10n_ro_account_period_close.current_liabilities")
        self.vat_paid = ref("l10n_ro_account_period_close.ova")
        self.vat_received = ref("l10n_ro_account_period_close.iva")
        self.vat_close_debit = ref("l10n_ro_account_period_close.cas")
        self.vat_close_credit = ref("l10n_ro_account_period_close.current_liabilities")
        self.exp_closing = self.per_close_model.create(
            {
                "name": "Closing Expenses",
                "type": "expense",
                "journal_id": self.misc_journal.id,
                "debit_account_id": self.debit_acc.id,
                "credit_account_id": self.credit_acc.id,
            }
        )
        self.inc_closing = self.per_close_model.create(
            {
                "name": "Closing Incomes",
                "type": "income",
                "journal_id": self.misc_journal.id,
                "close_result": True,
                "debit_account_id": self.debit_acc.id,
                "credit_account_id": self.credit_acc.id,
            }
        )
        self.vat_closing = self.per_close_model.create(
            {
                "name": "Closing VAT",
                "type": "selected",
                "account_ids": [(6, 0, [self.vat_paid.id, self.vat_received.id])],
                "journal_id": self.misc_journal.id,
                "debit_account_id": self.vat_close_debit.id,
                "credit_account_id": self.vat_close_credit.id,
            }
        )

    def test_period_closing(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_from = time.strftime("%Y-%m") + "-01"
        date_to = time.strftime("%Y-%m") + "-28"
        self.exp_closing.close(date_from, date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)
        self.inc_closing.close(date_from, date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)

    def test_period_closing_wizard(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_range = self.env["date.range"]
        self.type = self.env["date.range.type"].create(
            {"name": "Month", "company_id": False, "allow_overlap": False}
        )
        dt = date_range.create(
            {
                "name": "FS2016",
                "date_start": time.strftime("%Y-%m-01"),
                "date_end": time.strftime("%Y-%m-28"),
                "type_id": self.type.id,
            }
        )
        wizard = self.wiz_close_model.create(
            {
                "closing_id": self.vat_closing.id,
                "date_range_id": dt.id,
                "date_from": time.strftime("%Y-%m-28"),
                "date_to": time.strftime("%Y-%m-01"),
            }
        )
        wizard.onchange_date_range_id()
        self.assertEqual(
            wizard.date_from.strftime("%Y-%m-%d"), time.strftime("%Y-%m-01")
        )
        self.assertEqual(wizard.date_to.strftime("%Y-%m-%d"), time.strftime("%Y-%m-28"))
        wizard.do_close()

    def test_wizard_defaults(self):
        today = fields.Date.from_string(fields.Date.today())
        date_from = today + relativedelta(day=1, months=-1)
        date_to = today + relativedelta(day=1, days=-1)
        wizard = self.wiz_close_model.create({"closing_id": self.vat_closing.id})
        self.assertEqual(wizard.company_id.id, self.env.ref("base.main_company").id)
        self.assertEqual(
            wizard.date_from.strftime("%Y-%m-%d"), fields.Date.to_string(date_from)
        )
        self.assertEqual(
            wizard.date_to.strftime("%Y-%m-%d"), fields.Date.to_string(date_to)
        )
