# Copyright (C) 2022 Dakai Soft
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    stock_valuation_ids = fields.One2many(
        "stock.valuation.layer", "l10n_ro_stock_move_line_id"
    )

    @api.model
    def _create_correction_svl(self, move, diff):
        company_id = self.company_id
        if not self.company_id and self._context.get("default_company_id"):
            company_id = self.env["res.company"].browse(
                self._context["default_company_id"]
            )
        if not self.env["res.company"]._check_is_l10n_ro_record(company_id.id):
            return super(StockMoveLine, self)._create_correction_svl(move, diff)

        if diff < 0:
            raise ValidationError(
                _(
                    "You cannot decrease the quantity of a move line. "
                    "Please create a return."
                )
            )
        stock_valuation_layers = self.env["stock.valuation.layer"]
        for valued_type in move._get_valued_types():
            if getattr(move, "_is_%s" % valued_type)():
                if hasattr(move, "_create_%s_svl" % valued_type):
                    stock_valuation_layers |= getattr(
                        move, "_create_%s_svl" % valued_type
                    )(forced_quantity=diff)

        for svl in stock_valuation_layers:
            if not svl.product_id.valuation == "real_time":
                continue
            svl.stock_move_id._account_entry_move(
                svl.quantity, svl.description, svl.id, svl.value
            )
