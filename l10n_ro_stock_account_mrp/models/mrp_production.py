from odoo import models


class MrpProduction(models.Model):
    _name = "mrp.production"
    _inherit = ["mrp.production", "l10n.ro.mixin"]

    def _cal_price(self, consumed_moves):
        self.ensure_one()
        if not self.is_l10n_ro_record:
            return super()._cal_price(consumed_moves)

        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id
            and x.state not in ("done", "cancel")
            and x.quantity_done > 0
        )
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(
                    lambda x: x.date_end and not x.cost_already_recorded
                )
                duration = sum(time_lines.mapped("duration"))
                time_lines.write({"cost_already_recorded": True})
                work_center_cost += (
                    duration / 60.0
                ) * work_order.workcenter_id.costs_hour
            if finished_move.product_id.cost_method in ("fifo", "average"):
                qty_done = finished_move.product_uom._compute_quantity(
                    finished_move.quantity_done, finished_move.product_id.uom_id
                )
                extra_cost = self.extra_cost * qty_done
                finished_move.price_unit = (
                    sum(
                        -sum(m.stock_valuation_layer_ids.mapped("value"))
                        for m in consumed_moves.sudo()
                    )
                    + work_center_cost
                    + extra_cost
                ) / qty_done
        return True
