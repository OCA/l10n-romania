# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def write(self, vals):
        if "state" in vals and vals.get("state") == "posted":
            for move in self:
                if move.is_l10n_ro_record:
                    if (
                        not move.name or move.name == "/"
                    ) and move.journal_id.l10n_ro_journal_sequence_id:
                        new_number = (
                            move.journal_id.l10n_ro_journal_sequence_id.next_by_id()
                        )
                        super(AccountMove, move).write({"name": new_number})

        return super(AccountMove, self).write(vals)
