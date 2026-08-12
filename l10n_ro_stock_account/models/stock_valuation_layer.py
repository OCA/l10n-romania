# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models

VALUED_TYPE = [
    ("reception", "Reception"),
    ("reception_return", "Return reception"),
    ("reception_notice", "Reception with notice"),
    ("reception_notice_return", "Return reception with notice"),
    ("delivery", "Delivery"),
    ("delivery_return", "Return delivery"),
    ("delivery_notice", "Delivery with notice"),
    ("delivery_notice_return", "Return delivery with notice"),
    ("plus_inventory", "Plus inventory"),
    ("minus_inventory", "Minus inventory"),
    ("consumption", "Consumption"),
    ("consumption_return", "Return Consumption"),
    ("production", "Production"),
    ("production_return", "Return Production"),
    ("internal_transfer", "Internal Transfer"),
    ("internal_transfer_out", "Internal Transfer Out"),
    ("internal_transfer_in", "Internal Transfer In"),
    ("internal_transit", "Internal Transit"),  # de eliminat
    ("internal_transit_in", "Internal Transit In"),
    ("internal_transit_out", "Internal Transit In"),
    ("usage_giving", "Usage Giving"),
    ("usage_giving_return", "Return Usage Giving"),
    ("indefinite", "Indefinite"),
    ("dropshipped", "Dropshipped"),
]


class StockValuationLayer(models.Model):
    _name = "stock.valuation.layer"
    _inherit = ["stock.valuation.layer", "l10n.ro.mixin"]

    product_id = fields.Many2one(index=True)
    company_id = fields.Many2one(index=True)
    l10n_ro_valued_type = fields.Selection(VALUED_TYPE, string="Valued Type")

    l10n_ro_account_id = fields.Many2one(
        "account.account",
        compute="_compute_account",
        store=True,
        string="Valuation Account",
    )

    l10n_ro_invoice_line_id = fields.Many2one(
        "account.move.line", string="Romania Invoice Line"
    )
    l10n_ro_invoice_id = fields.Many2one("account.move", string="Invoice")

    @api.model_create_multi
    def create(self, vals_list):
        layers = super().create(vals_list)
        for layer in layers:
            if layer.stock_valuation_layer_id and not layer.l10n_ro_valued_type:
                layer.l10n_ro_valued_type = (
                    layer.stock_valuation_layer_id.l10n_ro_valued_type
                )
            if layer.stock_valuation_layer_id and not layer.stock_move_id:
                layer.stock_move_id = layer.stock_valuation_layer_id.stock_move_id
        return layers

    @api.depends("product_id", "account_move_id")
    def _compute_account(self):
        for svl in self.filtered(lambda sv: sv.stock_move_id.is_l10n_ro_record):
            account = self.env["account.account"]
            svl = svl.with_company(svl.stock_move_id.company_id)

            loc_dest = svl.stock_move_id.location_dest_id
            loc_scr = svl.stock_move_id.location_id
            account = (
                svl.product_id.l10n_ro_property_stock_valuation_account_id
                or svl.product_id.categ_id.property_stock_valuation_account_id
            )
            if svl.product_id.categ_id.l10n_ro_stock_account_change:
                # Pick the source/destination valuation account based on the
                # quantity sign, not the value sign. A zero-value move (e.g. a
                # 100% discounted / free product) has value == 0 on every layer,
                # so keying on ``value`` leaves both the out-leg and the in-leg
                # on the category default account, breaking the per-account stock
                # card (residual quantity on both warehouses). The quantity sign
                # always reflects the leg direction, including for value == 0.
                if (
                    svl.quantity > 0
                    and loc_dest.l10n_ro_property_stock_valuation_account_id
                ):
                    account = loc_dest.l10n_ro_property_stock_valuation_account_id
                if (
                    svl.quantity < 0
                    and loc_scr.l10n_ro_property_stock_valuation_account_id
                ):
                    account = loc_scr.l10n_ro_property_stock_valuation_account_id
            if svl.account_move_id and (
                not svl.l10n_ro_valued_type or "internal" not in svl.l10n_ro_valued_type
            ):
                # Some postings (e.g. landed costs split between capitalizing on
                # remaining stock and expensing to 607 the part already sold)
                # impact the SAME stock account through several lines whose
                # individual balances don't match ``svl.value`` on their own,
                # only their sum does. Matching a single line misses this case
                # and silently falls back to the category's default account,
                # leaving a stock-card residual on the correct account. Group
                # class 2/3 lines by account and match on the aggregated balance.
                #
                # A single journal entry can cover SEVERAL products (e.g. one
                # landed cost split across a whole shipment) — restrict the
                # aggregation to this layer's own product first, otherwise
                # unrelated products' lines on the same account get folded
                # into the sum and the match fails, or worse, coincidentally
                # matches the wrong total.
                candidate_lines = svl.account_move_id.line_ids.filtered(
                    lambda aml, product=svl.product_id: aml.product_id == product
                )
                by_account = {}
                for aml in candidate_lines:
                    if aml.account_id.code and aml.account_id.code[0] in ["2", "3"]:
                        by_account[aml.account_id] = (
                            by_account.get(aml.account_id, 0.0) + aml.balance
                        )
                for acc in sorted(by_account, key=lambda a: a.code or ""):
                    if round(by_account[acc], 2) == round(svl.value, 2):
                        account = acc
                        break
            if svl._l10n_ro_can_use_invoice_line_account(account):
                if (
                    svl.l10n_ro_valued_type in ("reception", "reception_return")
                    and svl.l10n_ro_invoice_line_id
                ):
                    account = svl.l10n_ro_invoice_line_id.account_id
            svl.l10n_ro_account_id = account

    def _l10n_ro_set_unit_cost(self, unit_cost):
        """Revalue the layers at ``unit_cost``, keeping their quantity.

        ``unit_cost`` is always positive; the sign of the value follows the
        sign of the quantity, so an out leg stays negative and an in leg stays
        positive.
        """
        for svl in self:
            currency = svl.company_id.currency_id
            svl.write(
                {
                    "unit_cost": unit_cost,
                    "value": currency.round(svl.quantity * unit_cost),
                    "remaining_value": currency.round(svl.remaining_qty * unit_cost),
                }
            )

    # hook method for reception in progress
    def _l10n_ro_can_use_invoice_line_account(self, account):
        self.ensure_one()
        return True

    def _validate_accounting_entries(self):
        res = super()._validate_accounting_entries()
        account_moves = self.mapped("account_move_id")
        account_moves = account_moves.filtered(
            lambda m: m.state == "draft" and m.move_type == "entry"
        )
        if account_moves:
            account_moves._post()

        return res
