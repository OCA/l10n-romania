# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from ast import literal_eval

from odoo import models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    def _is_dropshipped(self):
        if not self.is_l10n_ro_record:
            return False

        self.ensure_one()
        return (
            self.location_id.usage == "supplier"
            and self.location_dest_id.usage == "customer"
        )

    def _is_dropshipped_returned(self):
        if not self.is_l10n_ro_record:
            return super()._is_dropshipped()

        self.ensure_one()
        return (
            self.location_id.usage == "customer"
            and self.location_dest_id.usage == "supplier"
        )

    def action_l10n_ro_view_account_moves(self):
        self.ensure_one()
        domain = [("move_id.stock_move_id", "in", self.move_lines.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_stock_account.l10n_ro_stock_account_move_action"
        )
        context = literal_eval(action["context"])
        context.update(self.env.context)
        return dict(action, domain=domain, context=context)
