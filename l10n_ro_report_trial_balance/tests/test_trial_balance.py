# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time

from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class TestTrialBalanceReport(common.TransactionCase):

    def setUp(self):
        super(TestTrialBalanceReport, self).setUp()
        group_obj = self.env['account.group']
        acc_obj = self.env['account.account']
        self.account1 = acc_obj.create(
            {'code': '8999',
             'name': 'Account 8999',
             'user_type_id': self.env.ref(
                 'account.data_account_type_receivable').id,
             'reconcile': True})
        self.account2 = acc_obj.create(
            {'code': '89998',
             'name': 'Account 89998',
             'user_type_id': self.env.ref(
                 'account.data_account_type_receivable').id,
             'reconcile': True})
        self.account3 = acc_obj.create(
            {'code': '9999',
             'name': 'Account 9999',
             'user_type_id': self.env.ref(
                 'account.data_account_type_other_income').id})
        self.group1 = group_obj.create(
            {'code_prefix': '899',
             'name': 'Group 8'})
        self.group2 = group_obj.create(
            {'code_prefix': '89998',
             'name': 'Group 89998',
             'parent_id': self.group1.id})
        self.group3 = group_obj.create(
            {'code_prefix': '999',
             'name': 'Group 999'})
        self.previous_fy_date_start = '2015-01-01'
        self.previous_fy_date_end = '2015-12-31'
        self.fy_date_start = '2016-01-01'
        self.date_start = '2016-02-01'
        self.date_end = '2016-02-28'

    def _add_move(
            self,
            date,
            receivable_debit,
            receivable_credit,
            income_debit,
            income_credit,
            unaffected_debit=0,
            unaffected_credit=0
    ):
        move_name = 'expense accrual'
        journal = self.env['account.journal'].search([
            ('code', '=', 'MISC')])
        move_vals = {
            'journal_id': journal.id,
            'name': move_name,
            'date': date,
            'line_ids': [
                (0, 0, {
                    'name': move_name,
                    'debit': receivable_debit,
                    'credit': receivable_credit,
                    'account_id': self.account1.id}),
                (0, 0, {
                    'name': move_name,
                    'debit': income_debit,
                    'credit': income_credit,
                    'account_id': self.account3.id}),
                (0, 0, {
                    'name': move_name,
                    'debit': unaffected_debit,
                    'credit': unaffected_credit,
                    'account_id': self.account2.id}),
                ]}
        move = self.env['account.move'].create(move_vals)
        move.post()

    def _get_report_lines(self):
        company = self.env.ref('base.main_company')
        trial_balance = self.env['l10n_ro_report_trial_balance'].create({
            'date_from': self.date_start,
            'date_to': self.date_end,
            'only_posted_moves': True,
            'hide_account_balance_at_0': False,
            'company_id': company.id,
            'with_special_accounts': True,
            })
        trial_balance.compute_data_for_report()
        lines = {}
        report_account_model = self.env['l10n_ro_report_trial_balance_account']
        lines['receivable'] = report_account_model.search([
            ('report_id', '=', trial_balance.id),
            ('account_id', '=', self.account1.id),
        ])
        lines['income'] = report_account_model.search([
            ('report_id', '=', trial_balance.id),
            ('account_id', '=', self.account3.id),
        ])
        lines['unaffected'] = report_account_model.search([
            ('report_id', '=', trial_balance.id),
            ('account_id', '=', self.account2.id),
        ])
        lines['group1'] = report_account_model.search([
            ('report_id', '=', trial_balance.id),
            ('account_group_id', '=', self.group1.id),
        ])
        lines['group3'] = report_account_model.search([
            ('report_id', '=', trial_balance.id),
            ('account_group_id', '=', self.group3.id),
        ])
        return lines

    def test_00_account_group(self):
        self.assertEqual(len(self.group1.compute_account_ids.ids), 2)
        self.assertEqual(len(self.group3.compute_account_ids.ids), 1)

    def test_01_account_balance(self):
        # Generate the general ledger line
        lines = self._get_report_lines()
        self.assertEqual(len(lines['receivable']), 1)
        self.assertEqual(len(lines['income']), 1)

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000
        )

        # Re Generate the trial balance line
        lines = self._get_report_lines()
        self.assertEqual(len(lines['receivable']), 1)
        self.assertEqual(len(lines['income']), 1)

        # Check the initial and final balance
        self.assertEqual(lines['receivable'].debit_opening, 1000)
        self.assertEqual(lines['receivable'].credit_opening, 0)
        self.assertEqual(lines['receivable'].debit_initial, 0)
        self.assertEqual(lines['receivable'].credit_initial, 0)
        self.assertEqual(lines['receivable'].debit, 0)
        self.assertEqual(lines['receivable'].credit, 0)
        self.assertEqual(lines['receivable'].debit_total, 1000)
        self.assertEqual(lines['receivable'].credit_total, 0)
        self.assertEqual(lines['receivable'].debit_balance, 1000)
        self.assertEqual(lines['receivable'].credit_balance, 0)

        self.assertEqual(lines['group1'].debit_opening, 1000)
        self.assertEqual(lines['group1'].credit_opening, 0)
        self.assertEqual(lines['group1'].debit_initial, 0)
        self.assertEqual(lines['group1'].credit_initial, 0)
        self.assertEqual(lines['group1'].debit, 0)
        self.assertEqual(lines['group1'].credit, 0)
        self.assertEqual(lines['group1'].debit_total, 1000)
        self.assertEqual(lines['group1'].credit_total, 0)
        self.assertEqual(lines['group1'].debit_balance, 1000)
        self.assertEqual(lines['group1'].credit_balance, 0)

        # Add reversale move of the initial move the first day of fiscal year
        # to check the first day of fiscal year is not used
        # to compute the initial balance
        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0
        )

        # Re Generate the trial balance line
        lines = self._get_report_lines()
        self.assertEqual(len(lines['receivable']), 1)
        self.assertEqual(len(lines['income']), 1)

        # Check the initial and final balance
        self.assertEqual(lines['receivable'].debit_opening, 1000)
        self.assertEqual(lines['receivable'].credit_opening, 0)
        self.assertEqual(lines['receivable'].debit_initial, 0)
        self.assertEqual(lines['receivable'].credit_initial, 1000)
        self.assertEqual(lines['receivable'].debit, 0)
        self.assertEqual(lines['receivable'].credit, 0)
        self.assertEqual(lines['receivable'].debit_total, 1000)
        self.assertEqual(lines['receivable'].credit_total, 1000)
        self.assertEqual(lines['receivable'].debit_balance, 0)
        self.assertEqual(lines['receivable'].credit_balance, 0)

        self.assertEqual(lines['income'].debit_opening, 0)
        self.assertEqual(lines['income'].credit_opening, 1000)
        self.assertEqual(lines['income'].debit_initial, 1000)
        self.assertEqual(lines['income'].credit_initial, 0)
        self.assertEqual(lines['income'].debit, 0)
        self.assertEqual(lines['income'].credit, 0)
        self.assertEqual(lines['income'].debit_total, 1000)
        self.assertEqual(lines['income'].credit_total, 1000)
        self.assertEqual(lines['income'].debit_balance, 0)
        self.assertEqual(lines['income'].credit_balance, 0)

        self.assertEqual(lines['group1'].debit_opening, 1000)
        self.assertEqual(lines['group1'].credit_opening, 0)
        self.assertEqual(lines['group1'].debit_initial, 0)
        self.assertEqual(lines['group1'].credit_initial, 1000)
        self.assertEqual(lines['group1'].debit, 0)
        self.assertEqual(lines['group1'].credit, 0)
        self.assertEqual(lines['group1'].debit_total, 1000)
        self.assertEqual(lines['group1'].credit_total, 1000)
        self.assertEqual(lines['group1'].debit_balance, 0)
        self.assertEqual(lines['group1'].credit_balance, 0)

        self.assertEqual(lines['group3'].debit_opening, 0)
        self.assertEqual(lines['group3'].credit_opening, 1000)
        self.assertEqual(lines['group3'].debit_initial, 1000)
        self.assertEqual(lines['group3'].credit_initial, 0)
        self.assertEqual(lines['group3'].debit, 0)
        self.assertEqual(lines['group3'].credit, 0)
        self.assertEqual(lines['group3'].debit_total, 1000)
        self.assertEqual(lines['group3'].credit_total, 1000)
        self.assertEqual(lines['group3'].debit_balance, 0)
        self.assertEqual(lines['group3'].credit_balance, 0)

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.date_end,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0
        )

        # Re Generate the trial balance line
        lines = self._get_report_lines()
        self.assertEqual(len(lines['receivable']), 1)
        self.assertEqual(len(lines['income']), 1)

        # Check the initial and final balance
        self.assertEqual(lines['receivable'].debit_opening, 1000)
        self.assertEqual(lines['receivable'].credit_opening, 0)
        self.assertEqual(lines['receivable'].debit_initial, 0)
        self.assertEqual(lines['receivable'].credit_initial, 1000)
        self.assertEqual(lines['receivable'].debit, 0)
        self.assertEqual(lines['receivable'].credit, 1000)
        self.assertEqual(lines['receivable'].debit_total, 1000)
        self.assertEqual(lines['receivable'].credit_total, 2000)
        self.assertEqual(lines['receivable'].debit_balance, 0)
        self.assertEqual(lines['receivable'].credit_balance, 1000)

        self.assertEqual(lines['income'].debit_opening, 0)
        self.assertEqual(lines['income'].credit_opening, 1000)
        self.assertEqual(lines['income'].debit_initial, 1000)
        self.assertEqual(lines['income'].credit_initial, 0)
        self.assertEqual(lines['income'].debit, 1000)
        self.assertEqual(lines['income'].credit, 0)
        self.assertEqual(lines['income'].debit_total, 2000)
        self.assertEqual(lines['income'].credit_total, 1000)
        self.assertEqual(lines['income'].debit_balance, 1000)
        self.assertEqual(lines['income'].credit_balance, 0)

        self.assertEqual(lines['group1'].debit_opening, 1000)
        self.assertEqual(lines['group1'].credit_opening, 0)
        self.assertEqual(lines['group1'].debit_initial, 0)
        self.assertEqual(lines['group1'].credit_initial, 1000)
        self.assertEqual(lines['group1'].debit, 0)
        self.assertEqual(lines['group1'].credit, 1000)
        self.assertEqual(lines['group1'].debit_total, 1000)
        self.assertEqual(lines['group1'].credit_total, 2000)
        self.assertEqual(lines['group1'].debit_balance, 0)
        self.assertEqual(lines['group1'].credit_balance, 1000)

        self.assertEqual(lines['group3'].debit_opening, 0)
        self.assertEqual(lines['group3'].credit_opening, 1000)
        self.assertEqual(lines['group3'].debit_initial, 1000)
        self.assertEqual(lines['group3'].credit_initial, 0)
        self.assertEqual(lines['group3'].debit, 1000)
        self.assertEqual(lines['group3'].credit, 0)
        self.assertEqual(lines['group3'].debit_total, 2000)
        self.assertEqual(lines['group3'].credit_total, 1000)
        self.assertEqual(lines['group3'].debit_balance, 1000)
        self.assertEqual(lines['group3'].credit_balance, 0)

    def test_wizard_date_range(self):
        trial_balance_wizard = self.env['l10n.ro.report.trial.balance.wizard']
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
        wizard = trial_balance_wizard.create(
            {'date_range_id': dt.id,
             'date_from': time.strftime('%Y-%m-28'),
             'date_to': time.strftime('%Y-%m-01'),
             'target_move': 'posted'})
        wizard.onchange_date_range_id()
        self.assertEqual(wizard.date_from, time.strftime('%Y-%m-01'))
        self.assertEqual(wizard.date_to, time.strftime('%Y-%m-28'))
        wizard._export('qweb-pdf')
        wizard.button_export_html()
        wizard.button_export_pdf()
        wizard.button_export_xlsx()
