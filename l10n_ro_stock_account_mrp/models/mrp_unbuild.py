from ast import literal_eval

from odoo import fields, models


class MrpUnbuild(models.Model):
    _name = "mrp.unbuild"
    _inherit = ["mrp.unbuild", "l10n.ro.mixin"]

    l10n_ro_show_valuation = fields.Boolean(compute="_compute_l10n_roshow_valuation")

    def _compute_l10n_roshow_valuation(self):
        l10n_recs = self.filtered(lambda ub: ub.is_l10n_ro_record)
        for order in l10n_recs:
            order.l10n_ro_show_valuation = any(
                m.state == "done" for m in order.produce_line_ids
            )
        for order in self - l10n_recs:
            order.l10n_ro_show_valuation = False

    def action_l10n_ro_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [
            (
                "id",
                "in",
                (
                    self.produce_line_ids + self.consume_line_ids
                ).stock_valuation_layer_ids.ids,
            )
        ]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_account.stock_valuation_layer_action"
        )
        context = literal_eval(action["context"])
        context.update(self.env.context)
        context["no_at_date"] = True
        context["search_default_group_by_product_id"] = False
        return dict(action, domain=domain, context=context)
