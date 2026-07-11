# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    @api.model
    def get_bindings(self, model_name):
        """Drop the Romanian-specific contextual actions (the ones defined by
        an ``l10n_ro*`` module) from the "Action" menu / toolbar when the
        current company is not a Romanian company."""
        result = super().get_bindings(model_name)
        if not result or self.env.company._check_is_l10n_ro_record():
            return result
        action_ids = [
            action["id"]
            for actions in result.values()
            for action in actions
            if action.get("id")
        ]
        if not action_ids:
            return result
        ro_ids = set(
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("model", "=like", "ir.actions.%"),
                    ("res_id", "in", action_ids),
                    ("module", "=like", "l10n_ro%"),
                ]
            )
            .mapped("res_id")
        )
        if not ro_ids:
            return result
        filtered = {}
        for binding_type, actions in result.items():
            kept = [action for action in actions if action.get("id") not in ro_ids]
            if kept:
                filtered[binding_type] = kept
        return filtered
