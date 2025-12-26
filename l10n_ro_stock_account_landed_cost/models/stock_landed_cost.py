# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _name = "stock.landed.cost"
    _inherit = ["stock.landed.cost", "l10n.ro.mixin"]

    l10n_ro_cost_type = fields.Selection(
        [("normal", "Normal")],
        default="normal",
        string="Landed Cost Type",
    )
    l10n_ro_only_on_distributed_lines = fields.Boolean(
        help="Field used to stop distribution on the actual stock moves, "
        "and to distribute only on new field, distributed valuation lines.",
        compute="_compute_l10n_ro_only_on_distributed_lines",
        store=True,
        readonly=False,
    )
    l10n_ro_distributed_valuation_lines = fields.One2many(
        "l10n.ro.stock.valuation.adjustment.lines",
        "cost_id",
        string="Romania - Distributed Valuation Lines",
        readonly=True,
    )

    def _compute_l10n_ro_only_on_distributed_lines(self):
        """Method to compute if the landed cost will be distributed
        on actul stock move, or only on the distributed lines.
        e.g. For price difference, we should only distribute on the next moves,
        because the value in accounting is posted on the invoice.
        Transport or DVI should distribute on both."""
        for cost in self:
            cost.l10n_ro_only_on_distributed_lines = False

    def _check_sum(self):
        """Since we don't distribute the landed cost, adjust the check sum
        not to raise an error when validating them."""
        not_distributed_costs = self.filtered(
            lambda c: c.l10n_ro_only_on_distributed_lines
        )
        res = super(StockLandedCost, self - not_distributed_costs)._check_sum()
        for landed_cost in not_distributed_costs:
            total_amount = sum(
                landed_cost.l10n_ro_distributed_valuation_lines.mapped(
                    "additional_landed_cost"
                )
            )
            lc_total = 0
            for line in landed_cost.valuation_adjustment_lines:
                lc_total += (
                    (line.move_id.quantity - line.move_id.remaining_qty)
                    / line.move_id.quantity
                    * line.l10n_ro_not_distributed_amount
                )
            if not landed_cost.currency_id.is_zero(total_amount - lc_total):
                return False
        return res

    def button_validate(self):
        res = super().button_validate()
        for cost in self:
            for dist_line in cost.l10n_ro_distributed_valuation_lines:
                dist_line.move_id._set_value()
        return res

    def compute_landed_cost(self):
        # Extend method to handle Romania specific accounting entries
        # for landed costs, will calculate on moves quantity,
        # and create separate stock valuation layers
        # for each stock move destination
        res = super().compute_landed_cost()
        ro_landed_costs = self.filtered(lambda c: c.company_id.l10n_ro_accounting)
        if ro_landed_costs:
            ro_landed_costs._l10n_ro_distribute_landed_cost()
        for cost in ro_landed_costs:
            if cost.l10n_ro_only_on_distributed_lines:
                for line in cost.valuation_adjustment_lines:
                    line.l10n_ro_not_distributed_amount = line.additional_landed_cost
                    line.additional_landed_cost = 0
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
    l10n_ro_not_distributed_amount = fields.Monetary(
        "Not Distributed Amount", readonly=True
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
        res = []
        ro_adj_lines = self.filtered(lambda line: line.cost_id.is_l10n_ro_record)
        if self - ro_adj_lines:
            res = super(
                AdjustmentLines, self - ro_adj_lines
            )._create_accounting_entries(remaining_qty)
        if not res:
            res = []
        for line in ro_adj_lines:
            line = line.with_context(l10n_ro_stock_move=line.move_id)
            res += super(AdjustmentLines, line)._create_accounting_entries(
                line.move_id.quantity
            )
            line._l10n_ro_get_extra_accounting_entries()
            for distributed_line in line.l10n_ro_distributed_valuation_lines:
                res += distributed_line._create_accounting_entries()
        return res

    def _l10n_ro_get_extra_accounting_entries(self):
        """Get extra accounting entries for Romania landed cost."""
        self.ensure_one()
        ro_types = [
            "reception_notice",
            "reception_notice_return",
            "reception_in_progress",
            "reception_in_progress_return",
        ]
        account_move = self.env["account.move"]
        if (
            self.cost_id.l10n_ro_only_on_distributed_lines
            and self.move_id.l10n_ro_move_type in ro_types
        ):
            account_list = self.move_id._get_l10n_ro_move_type_account_list()
            aml_vals_list = self.move_id._get_l10n_ro_move_line_vals_list(
                account_list, [], forced_value=self.l10n_ro_not_distributed_amount
            )
            if aml_vals_list:
                account_move = self.env["account.move"].create(
                    {
                        "l10n_ro_extra_stock_move_id": self.move_id.id,
                        "journal_id": self.cost_id.account_journal_id.id,
                        "line_ids": [
                            Command.create(aml_vals) for aml_vals in aml_vals_list
                        ],
                    }
                )
                account_move._post()
        return account_move


class L10NROStockValuationAdjustmentLines(models.Model):
    _name = "l10n.ro.stock.valuation.adjustment.lines"
    _inherit = "stock.valuation.adjustment.lines"
    _description = "Romania - EXtra Stock Valuation Adjustment Lines"

    origin_line_id = fields.Many2one(
        "stock.valuation.adjustment.lines",
        string="Origin Adjustment Line",
        readonly=True,
    )

    def _create_accounting_entries(self):
        aml_vals_list = []
        if not self.move_id.l10n_ro_move_type:
            raise UserError(
                self.env._(
                    "Romanian Stock Move Type not set on stock move %(move)s",
                    move=self.move_id.display_name,
                )
            )
        account_list = self.move_id._get_l10n_ro_move_type_account_list()
        aml_vals_list = self.move_id._get_l10n_ro_move_line_vals_list(
            account_list, aml_vals_list, self.additional_landed_cost
        )
        # In case of return reception, create extra accounting entry
        # for notice or reception in progress
        extra_account_list = []
        extra_aml_vals_list = []
        if self.move_id.l10n_ro_move_type in [
            "reception_notice_return",
            "reception_in_progress_return",
        ]:
            extra_account_list = self.move_id._get_l10n_ro_move_type_account_list()
            extra_aml_vals_list = self.move_id._get_l10n_ro_move_line_vals_list(
                extra_account_list,
                extra_aml_vals_list,
                forced_value=self.additional_landed_cost,
            )
        if self.move_id.l10n_ro_move_type in ["usage_giving", "usage_giving_return"]:
            extra_account_list += (
                self.move_id._get_l10n_ro_move_type_account_list_extra()
            )
            extra_aml_vals_list = self.move_id._get_l10n_ro_move_line_vals_list(
                extra_account_list,
                extra_aml_vals_list,
                forced_value=self.additional_landed_cost,
            )
        if extra_aml_vals_list:
            account_move = self.env["account.move"].create(
                {
                    "l10n_ro_extra_stock_move_id": self.move_id.id,
                    "journal_id": self.cost_id.account_journal_id.id,
                    "line_ids": [
                        Command.create(aml_vals) for aml_vals in extra_aml_vals_list
                    ],
                }
            )
            if account_move:
                account_move._post()
        return [Command.create(aml_vals) for aml_vals in aml_vals_list]
