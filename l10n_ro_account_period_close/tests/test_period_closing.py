# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import time
from dateutil.relativedelta import relativedelta

from odoo import fields, tools
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


class TestCurrencyReevaluation(TransactionCase):
    def _load(self, module, *args):
        tools.convert_file(self.cr, 'l10n_ro_account_period_close',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test',
                           self.registry._assertion_report)

    def setUp(cls):
        super(TestCurrencyReevaluation, cls).setUp()
        ref = cls.env.ref
        cls.per_close_model = cls.env['account.period.closing']
        cls.wiz_close_model = cls.env['account.period.closing.wizard']
        # Load minimal account chart
        cls._load('account', 'test', 'account_minimal_test.xml')

        cls.misc_journal = ref(
            'l10n_ro_account_period_close.miscellaneous_journal')
        cls.debit_acc = ref(
            'l10n_ro_account_period_close.a_current_year_earnings')
        cls.credit_acc = ref(
            'l10n_ro_account_period_close.a_current_year_earnings')
        cls.vat_paid = ref('l10n_ro_account_period_close.ova')
        cls.vat_received = ref('l10n_ro_account_period_close.iva')
        cls.vat_close_debit = ref('l10n_ro_account_period_close.cas')
        cls.vat_close_credit = ref(
            'l10n_ro_account_period_close.current_liabilities')
        cls.exp_closing = cls.per_close_model.create(
            {'name': 'Closing Expenses',
             'type': 'expense',
             'journal_id': cls.misc_journal.id,
             'debit_account_id': cls.debit_acc.id,
             'credit_account_id': cls.credit_acc.id})
        cls.inc_closing = cls.per_close_model.create(
            {'name': 'Closing Incomes',
             'type': 'income',
             'journal_id': cls.misc_journal.id,
             'close_result': True,
             'debit_account_id': cls.debit_acc.id,
             'credit_account_id': cls.credit_acc.id})
        cls.vat_closing = cls.per_close_model.create(
            {'name': 'Closing VAT',
             'type': 'selected',
             'account_ids': [(6, 0, [cls.vat_paid.id, cls.vat_received.id])],
             'journal_id': cls.misc_journal.id,
             'debit_account_id': cls.vat_close_debit.id,
             'credit_account_id': cls.vat_close_credit.id})

    def test_period_closing(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_from = time.strftime('%Y-%m')+'-01'
        date_to = time.strftime('%Y-%m')+'-28'
        self.exp_closing.close(date_from, date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)
        self.inc_closing.close(date_from, date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)

    def test_period_closing_wizard(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_range = self.env['date.range']
        self.type = self.env['date.range.type'].create(
            {'name': 'Month',
             'company_id': False,
             'allow_overlap': False})
        dt = date_range.create({
            'name': 'FS2016',
            'date_start': time.strftime('%Y-%m-01'),
            'date_end': time.strftime('%Y-%m-28'),
            'type_id': self.type.id,
        })
        wizard = self.wiz_close_model.create(
            {'closing_id': self.vat_closing.id,
             'date_range_id': dt.id,
             'date_from': time.strftime('%Y-%m-28'),
             'date_to': time.strftime('%Y-%m-01')})
        wizard.onchange_date_range_id()
        self.assertEqual(wizard.date_from, time.strftime('%Y-%m-01'))
        self.assertEqual(wizard.date_to, time.strftime('%Y-%m-28'))
        wizard.do_close()

    def test_wizard_defaults(self):
        today = fields.Date.from_string(fields.Date.today())
        date_from = today + relativedelta(day=1, months=-1)
        date_to = today + relativedelta(day=1, days=-1)
        wizard = self.wiz_close_model.create(
            {'closing_id': self.vat_closing.id})
        self.assertEqual(wizard.company_id.id,
                         self.env.ref('base.main_company').id)
        self.assertEqual(wizard.date_from, fields.Date.to_string(date_from))
        self.assertEqual(wizard.date_to, fields.Date.to_string(date_to))
