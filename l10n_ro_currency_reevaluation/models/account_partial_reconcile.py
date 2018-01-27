# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model
    def _prepare_exchange_diff_partial_reconcile(
            self, aml, line_to_reconcile, currency):
        country = self.env.user.company_id.country_id
        if country.id == self.env.ref('base.ro').id:
            lrec = line_to_reconcile
            return {
                'debit_move_id': aml.credit and lrec.id or aml.id,
                'credit_move_id': aml.debit and lrec.id or aml.id,
                'amount': abs(lrec.debit - lrec.credit),
                'amount_currency': abs(lrec.amount_currency),
                'currency_id': currency.id,
            }
        return super(
            AccountPartialReconcile,
            self)._prepare_exchange_diff_partial_reconcile(
                aml, line_to_reconcile, currency)

    @api.model
    def create_exchange_rate_entry(self, aml_to_fix, amount_diff,
                                   diff_in_currency, currency, move):
        """
        Automatically create a journal items to book the exchange rate
        differences that can occure in multi-currencies environment. That
        new journal item will be made into the given `move` in the company
        `currency_exchange_journal_id`, and one of its journal items is
        matched with the other lines to balance the full reconciliation.

        :param aml_to_fix: recordset of account.move.line (possible several
            but sharing the same currency)
        :param amount_diff: float. Amount in company currency to fix
        :param diff_in_currency: float. Amount in foreign currency `currency`
            to fix
        :param currency: res.currency
        :param move: account.move
        :return: tuple.
            [0]: account.move.line created to balance the `aml_to_fix`
            [1]: recordset of account.partial.reconcile created between the
                tuple first element and the `aml_to_fix`
        """
        ctx = dict(self._context)
        country = self.env.user.company_id.country_id
        if country.id == self.env.ref('base.ro').id:
            if amount_diff != 0:
                partial_rec = self.env['account.partial.reconcile']
                aml_model = self.env['account.move.line']

                amount_diff = move.company_id.currency_id.round(amount_diff)
                diff_curr = currency.round(diff_in_currency) if \
                    currency else 0

                created_lines = self.env['account.move.line']
                ctx['check_move_validity'] = False
                exchange_journal = move.company_id.currency_exchange_journal_id
                for aml in aml_to_fix:
                    # create the line that will compensate all the aml_to_fix
                    line_to_rec = aml_model.with_context(ctx).create({
                        'name': _('Currency exchange rate difference'),
                        'debit': amount_diff < 0 and -amount_diff or 0.0,
                        'credit': amount_diff > 0 and amount_diff or 0.0,
                        'account_id': aml.account_id.id,
                        'move_id': move.id,
                        'currency_id': currency.id,
                        'amount_currency': -diff_curr,
                        'partner_id': aml.partner_id.id,
                        'currency_reevaluation': True
                    })
                    # create the counterpart on exchange gain/loss account
                    if amount_diff > 0:
                        new_acc = exchange_journal.default_debit_account_id.id
                    else:
                        new_acc = exchange_journal.default_credit_account_id.id
                    aml_model.with_context(ctx).create({
                        'name': _('Currency exchange rate difference'),
                        'debit': amount_diff > 0 and amount_diff or 0.0,
                        'credit': amount_diff < 0 and -amount_diff or 0.0,
                        'account_id': new_acc,
                        'move_id': move.id,
                        'currency_id': currency.id,
                        'amount_currency': diff_curr,
                        'partner_id': aml.partner_id.id,
                        'currency_reevaluation': True
                    })

                    # reconcile all aml_to_fix
                    ctx['skip_full_reconcile_check'] = \
                        'amount_currency_excluded'
                    partial_rec |= self.with_context(ctx).create(
                        self._prepare_exchange_diff_partial_reconcile(
                            aml=aml,
                            line_to_reconcile=line_to_rec,
                            currency=currency)
                    )
                    created_lines |= line_to_rec
                return created_lines, partial_rec
        else:
            super(AccountPartialReconcile, self).create_exchange_rate_entry(
                aml_to_fix, amount_diff, diff_in_currency, currency, move)

    def _compute_partial_lines(self):
        country = self.env.user.company_id.country_id
        if country.id == self.env.ref('base.ro').id:
            full_rec_model = self.env['account.full.reconcile']
            if self._context.get('skip_full_reconcile_check'):
                # when running the manual reconciliation wizard, don't check
                # the partials separately for full reconciliation or exchange
                # rate because it is handled manually after the whole
                # processing
                return self
            # check if the reconcilation is full
            # first, gather all journal items involved in the reconciliation
            # just created
            aml_set = aml_to_balance = self.env['account.move.line']
            total_debit = total_credit = total_amount_currency = old_amount = 0
            # make sure that all partial reconciliations share the same
            # secondary currency otherwise it's not possible to compute
            # the exchange difference entry and it has to be done manually.
            currency = self[0].currency_id
            maxdate = '0000-00-00'

            seen = set()
            todo = set(self)
            while todo:
                partial_rec = todo.pop()
                seen.add(partial_rec)
                if partial_rec.currency_id != currency:
                    # no exchange rate entry will be created
                    currency = None
                for aml in [partial_rec.debit_move_id,
                            partial_rec.credit_move_id]:
                    if aml not in aml_set:
                        if not aml.currency_reevaluation and (
                                aml.amount_residual or
                                aml.amount_residual_currency):
                            aml_to_balance |= aml
                        maxdate = max(aml.date, maxdate)
                first_day = fields.Date.from_string(maxdate).replace(day=1)
                if aml_to_balance:
                    move_date = fields.Date.from_string(aml_to_balance[0].date)
                else:
                    move_date = first_day
                if move_date < first_day:
                    reevaluation_date = first_day
                else:
                    reevaluation_date = move_date
                for aml in [partial_rec.debit_move_id,
                            partial_rec.credit_move_id]:
                    if aml not in aml_set:
                        total_debit += aml.debit
                        total_credit += aml.credit
                        aml_set |= aml
                        if aml.currency_id and aml.currency_id == currency:
                            total_amount_currency += aml.amount_currency
                        elif partial_rec.currency_id and \
                                partial_rec.currency_id == currency:
                            # if the aml has no secondary currency but is
                            # reconciled with other journal item in secondary
                            # currency, the amount currency is recorded on the
                            # partial rec and in order to check if the
                            # reconciliation is total, we need to convert the
                            # aml.balance in that foreign currency
                            total_amount_currency += \
                                aml.company_id.currency_id.with_context(
                                    date=reevaluation_date).compute(
                                        aml.balance, partial_rec.currency_id)

                    for line in aml.matched_debit_ids | aml.matched_credit_ids:
                        if line not in seen:
                            todo.add(line)

            partial_rec_ids = [x.id for x in seen]
            aml_ids = aml_set.ids
            # then, if the total debit and credit are equal, or the total
            # amount in currency is 0, the reconciliation is full
            digits_rounding_precision = \
                aml_set[0].company_id.currency_id.rounding
            old_amount = partial_rec.currency_id.with_context(
                date=reevaluation_date).compute(total_amount_currency,
                                                aml.company_id.currency_id)
            # Create a journal entry to book the difference due to foreign
            # currency's exchange rate that fluctuates
            if (currency and float_is_zero(
                    total_amount_currency,
                    precision_rounding=currency.rounding)) or float_compare(
                        total_debit - total_credit, old_amount,
                        precision_rounding=digits_rounding_precision) != 0:
                exchange_move_id = False
                if currency and aml_to_balance:
                    total_amount_currency = 0
                    exchange_move = self.env['account.move'].create(
                        full_rec_model._prepare_exchange_diff_move(
                            move_date=maxdate,
                            company=aml_to_balance[0].company_id))
                    # eventually create a journal entry to book the difference
                    # due to foreign currency's exchange rate that fluctuates
                    rate_diff_partial_rec = \
                        self.create_exchange_rate_entry(
                            aml_to_balance,
                            total_debit - total_credit - old_amount,
                            total_amount_currency,
                            currency,
                            exchange_move)[1]
                    partial_rec_ids += rate_diff_partial_rec.ids
                    exchange_move.post()
                    exchange_move_id = exchange_move.id
            if (currency and float_is_zero(
                    total_amount_currency,
                    precision_rounding=currency.rounding)):
                self.env['account.full.reconcile'].create({
                    'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                    'reconciled_line_ids': [(6, 0, aml_ids)],
                    'exchange_move_id': exchange_move_id,
                })
        else:
            return super(
                AccountPartialReconcile, self)._compute_partial_lines()
