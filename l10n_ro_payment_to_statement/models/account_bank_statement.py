# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _inherit = ["account.bank.statement", "l10n.ro.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.company._check_is_l10n_ro_record():
                if "journal_id" in vals:
                    journal_id = vals["journal_id"]
                else:
                    # la import jurnalul este in context
                    journal_id = self.env.context.get("default_journal_id", False)
                if (
                    "name" not in vals or vals["name"] in ["/", "", False]
                ) and journal_id:
                    journal = self.env["account.journal"].browse(journal_id)
                    if journal.l10n_ro_statement_sequence_id:
                        vals[
                            "name"
                        ] = journal.l10n_ro_statement_sequence_id.next_by_id()
                    else:
                        vals["name"] = fields.Date.to_string(fields.Date.today())
        return super(AccountBankStatement, self).create(vals_list)

    def name_get(self):
        result = super().name_get()
        result_dict = dict(result)
        for record in self:
            if record.is_l10n_ro_record and record.name == "/":
                result_dict[record.id] = fields.Date.to_string(record.date)
        return list(result_dict.items())


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherit = ["account.bank.statement.line", "l10n.ro.mixin"]

    is_l10n_ro_payment_disposal = fields.Boolean()
