# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class StockLandedCost(models.Model):
    _name = "stock.landed.cost"
    _inherit = ["stock.landed.cost", "l10n.ro.mixin"]

    l10n_ro_cost_type = fields.Selection(
        [("normal", "Normal")],
        default="normal",
        string="Landed Cost Type",
    )
    l10n_ro_distributed_valuation_lines = fields.One2many(
        "l10n.ro.stock.valuation.adjustment.lines",
        "cost_id",
        string="Romania - Distributed Valuation Lines",
        readonly=True,
    )

    def compute_landed_cost(self):
        # Extend method to handle Romania specific accounting entries
        # for landed costs, will calculate on moves quantity,
        # and create separate stock valuation layers
        # for each stock move destination
        res = super().compute_landed_cost()
        ro_landed_costs = self.filtered(lambda c: c.company_id.l10n_ro_accounting)
        if ro_landed_costs:
            ro_landed_costs._l10n_ro_distribute_landed_cost()
        return res

    @api.model
    def _get_l10n_ro_move_destinations(self, move):
        """Get recursive all destination moves for a given move."""
        dest_vals_list = []
        for track in move.l10n_ro_move_track_dest_ids:
            dest_vals_list.append(
                {
                    "move": track.dest_move_id,
                    "quantity": track.quantity,
                }
            )
            if track.dest_move_id.l10n_ro_move_track_dest_ids:
                dest_vals_list += self._get_l10n_ro_move_destinations(
                    track.dest_move_id
                )
        return dest_vals_list

    def _l10n_ro_distribute_landed_cost(self):
        """Distribute landed cost on stock moves quantity,
        creating separate l10n.ro.stock.valuation.adjustment.lines
        for each stock move destination."""
        AdjustementLines = self.env["l10n.ro.stock.valuation.adjustment.lines"]
        AdjustementLines.search([("cost_id", "in", self.ids)]).unlink()

        for cost in self:
            for line in cost.valuation_adjustment_lines:
                move = line.move_id
                if not move:
                    continue
                um_add_cost = line.additional_landed_cost / move.quantity
                move_dest_vals_list = self._get_l10n_ro_move_destinations(move)
                for dest_vals in move_dest_vals_list:
                    additional_landed_cost = um_add_cost * dest_vals["quantity"]
                    adj_line_vals = line._l10n_ro_prepare_adj_line_vals(
                        dest_vals, additional_landed_cost
                    )
                    self.env["l10n.ro.stock.valuation.adjustment.lines"].create(
                        adj_line_vals
                    )


class AdjustmentLines(models.Model):
    _name = "stock.valuation.adjustment.lines"
    _inherit = ["stock.valuation.adjustment.lines", "l10n.ro.mixin"]

    l10n_ro_distributed_valuation_lines = fields.One2many(
        "l10n.ro.stock.valuation.adjustment.lines",
        "origin_line_id",
        string="Romania - Distributed Valuation Lines",
        readonly=True,
    )

    def _l10n_ro_prepare_adj_line_vals(self, track_vals, additional_landed_cost):
        former_cost = track_vals["move"]._get_value()
        vals = {
            "cost_id": self.cost_id.id,
            "cost_line_id": self.cost_line_id.id,
            "origin_line_id": self.id,
            "move_id": track_vals["move"].id,
            "product_id": track_vals["move"].product_id.id,
            "quantity": track_vals["quantity"],
            "former_cost": former_cost,
            "additional_landed_cost": additional_landed_cost,
        }
        return vals

    def _create_accounting_entries(self, remaining_qty):
        """For Romania create accouting entries on total quantity of the move,
        as landed cost is distributed on move destinations."""
        ro_adj_lines = self.filtered(lambda line: line.cost_id.is_l10n_ro_record)
        res = super(AdjustmentLines, self - ro_adj_lines)._create_accounting_entries(
            remaining_qty
        )
        for line in ro_adj_lines:
            res += super(AdjustmentLines, line)._create_accounting_entries(
                line.move_id.quantity
            )
            for distributed_line in line.l10n_ro_distributed_valuation_lines:
                res += super(
                    AdjustmentLines, distributed_line
                )._create_accounting_entries(distributed_line.move_id.quantity)
        return res


class L10NROStockValuationAdjustmentLines(models.Model):
    _name = "l10n.ro.stock.valuation.adjustment.lines"
    _inherit = "stock.valuation.adjustment.lines"
