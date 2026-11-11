# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, tools


class L10nRoIrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    is_l10n_ro_record = fields.Boolean()

    @api.model
    @tools.ormcache(
        "frozenset(self.env.user._get_group_ids())",
        "debug",
        "self.env.company.l10n_ro_accounting",
    )
    def _visible_menu_ids(self, debug=False):
        """Hide the Romanian-specific menus (the ones defined by an
        ``l10n_ro*`` module) on non-Romanian companies, mirroring the way
        ``ir.actions.actions.get_bindings`` drops RO contextual actions."""
        visible = super()._visible_menu_ids(debug=debug)
        if not visible or self.env.company._check_is_l10n_ro_record():
            return visible
        ro_ids = set(
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("model", "=", "ir.ui.menu"),
                    ("res_id", "in", list(visible)),
                    ("module", "=like", "l10n_ro%"),
                ]
            )
            .mapped("res_id")
        )
        if not ro_ids:
            return visible
        return set(visible) - ro_ids
