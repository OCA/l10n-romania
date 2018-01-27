# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Remove constrain of account having the same currency as the journal
    @api.one
    @api.constrains('currency_id',
                    'default_credit_account_id',
                    'default_debit_account_id')
    def _check_currency(self):
        if not self.company_id.country_id == self.env.ref('base.ro'):
            return super(AccountJournal, self)._check_currency()


class AccountAccount(models.Model):
    _inherit = "account.account"

    currency_reevaluation = fields.Boolean("Allow Currency reevaluation")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    currency_reevaluation = fields.Boolean("Currency reevaluation")
