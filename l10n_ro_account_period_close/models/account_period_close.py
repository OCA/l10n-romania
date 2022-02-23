# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPeriodClosing(models.Model):
    _name = 'account.period.closing'
    _description = 'Account Period Closing'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    type = fields.Selection(
        [
            ('income', 'Incomes'),
            ('expense', 'Expenses'),
            ('selected', 'Selected')
        ], string='Type', required=True)
    close_result = fields.Boolean('Close debit and credit accounts')
    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True)
    account_ids = fields.Many2many(
        'account.account', string='Accounts to close')
    debit_account_id = fields.Many2one(
        'account.account',
        'Closing account, debit',
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    credit_account_id = fields.Many2one(
        'account.account',
        'Closing account, credit',
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    move_ids = fields.One2many('account.move', 'close_id', 'Closing Moves')

    @api.onchange('company_id', 'type')
    def _onchange_type(self):
        acc_type = False
        accounts = self.env['account.account']
        if self.type == 'income':
            acc_type = self.env.ref(
                'account.data_account_type_revenue').id
        elif self.type == 'expense':
            acc_type = self.env.ref(
                'account.data_account_type_expenses').id
        if acc_type:
            accounts = self.env['account.account'].search([
                ('user_type_id', '=', acc_type),
                ('company_id', '=', self.company_id.id)
            ])
        self.account_ids = accounts

    def _get_accounts(self, accounts, display_account):
        """ compute the balance, debit and credit for the provided accounts
            :Arguments:
                `accounts`: list of accounts record,
                `display_account`: it's used to display either all accounts or
                                   those accounts which balance is > 0
            :Returns a list of dict of Accounts with following key and value
                `name`: Account name,
                `code`: Account code,
                `credit`: total amount of credit,
                `debit`: total amount of debit,
                `balance`: total amount of balance,
        """

        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        # compute the balance, debit and credit for the provided accounts
        # pylint: disable=E8103
        request = ("SELECT account_id AS id, "
                   "SUM(debit) AS debit, "
                   "SUM(credit) AS credit, "
                   "(SUM(debit) - SUM(credit)) AS balance" +
                   " FROM " + tables +
                   " WHERE account_id IN %s " + filters +
                   " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id if account.currency_id else \
                account.company_id.currency_id
            res['id'] = account.id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and \
                    not currency.is_zero(res['balance']):
                account_res.append(res)
            if display_account == 'movement' and \
                    (not currency.is_zero(res['debit']) or
                     not currency.is_zero(res['credit'])):
                account_res.append(res)
        return account_res

    @api.multi
    def close(self, date_from=None, date_to=None):
        """ This method will create the closing move for the
            date interval selected."""
        account_obj = self.env['account.account']
        journal_id = self.journal_id.id
        for closing in self:
            ctx = self.env.context.copy()
            ctx['strict_range'] = True
            ctx['state'] = 'posted'
            ctx['date_from'] = date_from
            ctx['date_to'] = date_to
            account_res = self.with_context(ctx)._get_accounts(
                closing.account_ids, 'not_zero')
            move = self.env['account.move'].create({
                'date': date_to,
                'journal_id': journal_id,
                'close_id': closing.id,
                'company_id': closing.company_id.id
            })
            amount = 0.0
            for account in account_res:
                if account['balance'] != 0.0:
                    balance = account['balance']
                    check = account_obj.browse(account['id']).close_check
                    if closing.type == 'expense' and not check:
                        val = {
                            'name': 'Closing ' + closing.name,
                            'move_id': move.id,
                            'account_id': account['id'],
                            'credit': balance or 0.0,
                            'debit': 0.0,
                        }
                    elif closing.type == 'income' and not check:
                        val = {
                            'name': 'Closing ' + closing.name,
                            'move_id': move.id,
                            'account_id': account['id'],
                            'credit': 0.0,
                            'debit': (-1 * balance) or 0.0,
                        }
                    else:
                        val = {
                            'name': 'Closing ' + closing.name,
                            'move_id': move.id,
                            'account_id': account['id'],
                            'credit': balance if balance > 0.0 else 0.0,
                            'debit': -balance if balance < 0.0 else 0.0,
                        }
                    amount += balance
                    self.env['account.move.line'].with_context(
                        check_move_validity=False).create(val)

            diff_line = {
                'name': 'Closing ' + closing.name,
                'move_id': move.id,
                'account_id':
                    closing.debit_account_id.id if
                    amount >= 0 else closing.credit_account_id.id,
                'credit': -amount if amount <= 0.0 else 0.0,
                'debit': amount if amount >= 0.0 else 0.0,
            }
            self.env['account.move.line'].with_context(
                check_move_validity=False).create(diff_line)
            if self.close_result and amount != 0.0:
                debit_acc = closing.debit_account_id
                credit_acc = closing.credit_account_id
                debit = credit = new_amount = 0.0
                ctx1 = dict(self._context)
                ctx1.update({'date_from': False, 'date_to': date_to})
                accounts = account_obj.browse(
                    [closing.debit_account_id.id,
                     closing.credit_account_id.id])
                account_res = self.with_context(ctx1)._get_accounts(
                    accounts, 'all')
                for acc in account_res:
                    if acc['id'] == closing.debit_account_id.id:
                        debit = acc['balance']
                    if acc['id'] == closing.credit_account_id.id:
                        credit = acc['balance']
                    old_balance = debit - (-1 * credit)
                    if credit and debit:
                        if old_balance > 0:
                            debit_acc = closing.credit_account_id
                            credit_acc = closing.debit_account_id
                        elif old_balance < 0:
                            debit_acc = closing.debit_account_id
                            credit_acc = closing.credit_account_id
                if abs(debit) > abs(credit):
                    new_amount = -1 * credit
                else:
                    new_amount = debit
                diff_line = {
                    'name': 'Closing ' + closing.name +
                            ' ' + str(debit_acc.code),
                    'move_id': move.id,
                    'account_id': debit_acc.id,
                    'credit': new_amount,
                    'debit': 0.0,
                }
                self.env['account.move.line'].with_context(
                    check_move_validity=False).create(diff_line)
                diff_line = {
                    'name': 'Closing ' + closing.name +
                            ' ' + str(credit_acc.code),
                    'move_id': move.id,
                    'account_id': credit_acc.id,
                    'credit': 0.0,
                    'debit': new_amount,
                }
                self.env['account.move.line'].with_context(
                    check_move_validity=False).create(diff_line)
            move.post()
