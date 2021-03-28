# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    valued_type = fields.Char()
    invoice_line_id = fields.Many2one("account.move.line", string="Invoice Line")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    account_id = fields.Many2one(
        "account.account", compute="_compute_account", store=True
    )

    @api.depends("product_id", "account_move_id")
    def _compute_account(self):
        for svl in self:
            if not svl.account_move_id:
                loc_dest = svl.stock_move_id.location_dest_id
                loc_scr = svl.stock_move_id.location_id
                categ = svl.product_id.categ_id
                svl.account_id = categ.property_stock_valuation_account_id
                if svl.value > 0 and loc_dest.property_stock_valuation_account_id:
                    svl.account_id = loc_dest.property_stock_valuation_account_id
                if svl.value < 0 and loc_scr.property_stock_valuation_account_id:
                    svl.account_id = loc_scr.property_stock_valuation_account_id
            else:
                for aml in svl.account_move_id.line_ids:
                    if aml.credit > 0 and svl.value < 0:
                        svl.account_id = aml.account_id
                        break
                    if aml.debit > 0 and svl.value > 0:
                        svl.account_id = aml.account_id
                        break

    def init(self):
        """ This method will compute values for valuation layer valued_type"""
        val_layers = self.search(
            ["|", ("valued_type", "=", False), ("valued_type", "=", "")]
        )
        val_types = self.env["stock.move"]._get_valued_types()
        val_types = [
            val
            for val in val_types
            if val not in ["in", "out", "dropshipped", "dropshipped_returned"]
        ]
        for layer in val_layers:
            if layer.stock_move_id:
                for valued_type in val_types:
                    if getattr(layer.stock_move_id, "_is_%s" % valued_type)():
                        layer.valued_type = valued_type
                        continue

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "valued_type" not in values and "stock_valuation_layer_id" in values:
                svl = self.env["stock.valuation.layer"].browse(
                    values["stock_valuation_layer_id"]
                )
                if svl:
                    values["valued_type"] = svl.valued_type
        return super(StockValuationLayer, self).create(vals_list)

    def _compute_invoice_line_id(self):
        for svl in self:
            invoice_lines = self.env["account.move.line"]
            stock_move = svl.stock_move_id
            if "reception" in svl.valued_type:
                invoice_lines = stock_move.purchase_line_id.invoice_lines
            if "delivery" in svl.valued_type:
                invoice_lines = stock_move.sale_line_id.invoice_lines

            if len(invoice_lines) == 1:
                svl.invoice_line_id = invoice_lines
            else:
                for line in invoice_lines:
                    if stock_move.date.date() == line.move_id.date:
                        svl.invoice_line_id = line
