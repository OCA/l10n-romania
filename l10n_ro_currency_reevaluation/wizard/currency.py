# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class RomaniaCurrencyReevaluation(models.TransientModel):
    _name = 'l10n.ro.currency.reevaluation'

    date_reevaluation = fields.Date('Reevaluation Date', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, change_default=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'currency.reevaluation'),
        help="The company for which is the reevaluation.")

    @api.model
    def _get_accounts(self):
        account_obj = self.env['account.account']
        account_ids = [account.id for account in account_obj.search(
            [('currency_reevaluation', '=', True),
             ('company_id', '=', self.company_id.id)])]
        return account_ids

    @api.model
    def _get_lines_domain(self, account_ids, reevaluation_date):
        return [
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
            ('company_id', '=', self.company_id.id),
            ('currency_id', '!=', False),
            ('account_id', 'in', account_ids),
            ('date', '<=', reevaluation_date),
            ('currency_reevaluation', '!=', True)]

    @api.model
    def _get_lines(self, account_ids, reevaluation_date):
        move_obj = self.env['account.move.line']
        domain = self._get_lines_domain(account_ids, reevaluation_date)
        return move_obj.search(domain)

    @api.model
    def _get_line_balances(self, line, reevaluation_date):
        balance = line.debit - line.credit
        foreign_balance = line.amount_currency
        if line.matched_debit_ids:
            for partial in line.matched_debit_ids:
                rec_line = partial.debit_move_id
                if rec_line.date <= reevaluation_date:
                    balance += rec_line.debit - rec_line.credit
                    foreign_balance += rec_line.amount_currency
        if line.matched_credit_ids:
            for partial in line.matched_credit_ids:
                rec_line = partial.credit_move_id
                if rec_line.date <= reevaluation_date:
                    balance += rec_line.debit - rec_line.credit
                    foreign_balance += rec_line.amount_currency
        return (balance, foreign_balance)

    @api.model
    def _get_journal_balances(self, account_ids, reevaluation_date):
        query = """SELECT sum(aml.balance) as bal,
                          sum(aml.amount_currency) as bal_curr
                   FROM account_move_line aml
                   LEFT JOIN account_move as move ON move.id = aml.move_id
                   WHERE move.state = 'posted' AND aml.account_id in %s AND
                         aml.date <= %s;"""
        self.env.cr.execute(query, (account_ids, reevaluation_date,))
        query_results = self.env.cr.dictfetchall()
        bal = bal_curr = 0.00
        if query_results and query_results[0].get('bal') is not None:
            bal = query_results[0].get('bal')
        if query_results and query_results[0].get('bal_curr') is not None:
            bal_curr = query_results[0].get('bal_curr')
        return (bal, bal_curr)

    @api.multi
    def compute_difference(self):
        self.ensure_one()
        journal_obj = self.env['account.journal']
        move_obj = self.env['account.move']

        reevaluation_date = self.date_reevaluation
        company = self.company_id

        reeval_date = fields.Date.from_string(self.date_reevaluation)
        date_newrate = fields.Date.from_string(
            reevaluation_date) + relativedelta(day=1, months=+1)
        first_day = fields.Date.from_string(
            reevaluation_date) + relativedelta(day=1)

        ctx = dict(self._context)
        ctx.update({'date': date_newrate})

        ctx1 = dict(self._context)

        journal = self.company_id.currency_exchange_journal_id
        if company.expense_currency_exchange_account_id:
            expense_acc = company.expense_currency_exchange_account_id.id
        else:
            expense_acc = journal.default_debit_account_id.id
        if company.income_currency_exchange_account_id:
            income_acc = company.income_currency_exchange_account_id.id
        else:
            income_acc = journal.default_credit_account_id.id
        company_currency = company.currency_id

        # get account move lines with foreign currency posted before
        # reevaluation date (end of period)
        # balance and foreign balance are not taking in consideration newer
        # reconciliations
        created_ids = []
        account_ids = self._get_accounts()
        reeval_lines = self._get_lines(account_ids, reevaluation_date)
        if reeval_lines:
            move_vals = {
                'name': _('Currency exchange rate difference ') + str(
                    reevaluation_date),
                'journal_id': journal.id,
                'date': reevaluation_date}
            for line in reeval_lines:
                line_date = fields.Date.from_string(line.date)
                currency = line.currency_id
                balance, foreign_balance = self._get_line_balances(
                    line, reevaluation_date)
                if foreign_balance != 0.00:
                    new_amount = currency.with_context(ctx).compute(
                        foreign_balance, company_currency, round=True)
                    if (line_date >= first_day and
                            line_date <= reeval_date):
                        ctx1.update({'date': line_date})
                    else:
                        ctx1.update({'date': first_day})
                    old_amount = currency.with_context(ctx1).compute(
                        foreign_balance, company_currency, round=True)
                    round_bal = round(
                        balance,
                        company_currency.decimal_places)
                    if old_amount != round_bal:
                        old_amount = round_bal
                    amount = round(
                        old_amount - new_amount,
                        company_currency.decimal_places)
                    if amount != 0.00:
                        exchange_move = self.env['account.move'].create(
                            self.env[
                                'account.full.reconcile'
                            ]._prepare_exchange_diff_move(
                                move_date=fields.Date.to_string(reeval_date),
                                company=company))
                        # eventually create a journal entry to book the
                        # difference due to foreign currency's exchange
                        # rate that fluctuates
                        self.env[
                            'account.partial.reconcile'
                        ].create_exchange_rate_entry(line, amount, 0,
                                                     currency, exchange_move)
                        exchange_move._post_validate()
                        exchange_move.post()
                        created_ids.append(exchange_move.id)

        journals = journal_obj.search(
            [('type', 'in', ('cash', 'bank')),
             ('company_id', '=', company.id),
             ('currency_id', '!=', False)])
        for journal in journals:
            currency = journal.currency_id
            old_amount = 0.00
            account_ids = tuple(
                ac for ac in [journal.default_debit_account_id.id,
                              journal.default_credit_account_id.id] if ac)
            if account_ids:
                bal, bal_curr = self._get_journal_balances(
                    account_ids, reevaluation_date)
                new_amount = journal.currency_id.with_context(ctx).compute(
                    bal_curr, company_currency, round=True)
                amount = round(new_amount - bal,
                               company_currency.decimal_places)
                if amount != 0.00:
                    move_vals = {
                        'name': _('Currency exchange rate difference ') + str(
                            reevaluation_date),
                        'journal_id': journal.id,
                        'date': reevaluation_date}
                    if amount > 0:
                        eval_account = income_acc
                        journal_account = journal.default_debit_account_id
                        debit = abs(amount)
                        credit = 0.00
                    else:
                        eval_account = expense_acc
                        journal_account = journal.default_credit_account_id
                        debit = 0.00
                        credit = abs(amount)

                    valsm = {
                        'name': _('Currency exchange rate difference ') + str(
                            reevaluation_date),
                        'account_id': journal_account.id,
                        'debit': debit,
                        'credit': credit,
                        'amount_currency': 0.00,
                        'currency_id': currency.id,
                        'date': reevaluation_date,
                    }
                    valsm1 = {
                        'name': _('Currency exchange rate difference ') + str(
                            reevaluation_date),
                        'account_id': eval_account,
                        'debit': credit,
                        'credit': debit,
                        'amount_currency': 0.00,
                        'currency_id': currency.id,
                        'date': reevaluation_date,
                    }
                    move_vals['line_ids'] = [(0, 0, valsm), (0, 0, valsm1)]
                    move = move_obj.create(move_vals)
                    move._post_validate()
                    move.post()
                    created_ids.append(move.id)
        if created_ids:
            return {
                'name': _('Created reevaluation moves'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'domain': [('id', 'in', created_ids)],
            }
        return {'type': 'ir.actions.act_window_close'}
