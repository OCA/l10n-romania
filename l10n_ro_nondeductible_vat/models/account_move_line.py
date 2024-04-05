# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        moves = self.env["account.move"]
        to_remove_lines = self.env["account.move.line"]
        for line in lines.filtered(lambda l: l.company_id.l10n_ro_accounting):
            move = line.move_id
            company = line.company_id
            tax_rep_line = line.tax_repartition_line_id
            new_account = line.account_id
            # Set the account to the non deductible account or the
            # company non deductible account
            if tax_rep_line.l10n_ro_nondeductible:
                if company.l10n_ro_nondeductible_account_id:
                    new_account = company.l10n_ro_nondeductible_account_id
                if line.account_id.l10n_ro_nondeductible_account_id:
                    new_account = line.account_id.l10n_ro_nondeductible_account_id
            # Use company cash basis base account not to increase balances
            # of invoice accounts
            if (
                move.move_type == "entry"
                and tax_rep_line.l10n_ro_skip_cash_basis_account_switch
                and company.account_cash_basis_base_account_id
            ):
                new_account = company.account_cash_basis_base_account_id
            if line.account_id != new_account:
                line.account_id = new_account
            # Remove the lines marked to be removed from stock non deductible
            if (
                line.display_type == "tax"
                and move.stock_move_id.l10n_ro_nondeductible_tax_id
                and tax_rep_line.l10n_ro_exclude_from_stock
            ):
                moves |= line.move_id
                to_remove_lines |= line
        to_remove_lines.with_context(dynamic_unlink=True).sudo().unlink()
        moves._sync_dynamic_lines(container={"records": moves, "self": moves})
        return lines - to_remove_lines
