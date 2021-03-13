# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    print_report = fields.Boolean("Print in Report")


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def write(self, vals):
        result = super(AccountJournal, self).write(vals)
        for journal in self:
            # Write print_report if bank account was created
            if "print_report" in vals and journal.bank_account_id:
                journal.bank_account_id.print_report = vals.get("print_report")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        journals = self
        for vals in vals_list:
            journal = super(AccountJournal, self).create(vals)
            if "print_report" in vals and journal.bank_account_id:
                journal.bank_account_id.print_report = vals.get("print_report")
            journals |= journal
        return journals

    print_report = fields.Boolean(related="bank_account_id.print_report")
