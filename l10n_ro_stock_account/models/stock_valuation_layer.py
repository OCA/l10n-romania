# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _name = "stock.valuation.layer"
    _inherit = ["stock.valuation.layer", "l10n.ro.mixin"]

    l10n_ro_valued_type = fields.Char(string="Romania - Valued Type")
    l10n_ro_invoice_line_id = fields.Many2one(
        "account.move.line", string="Romania - Invoice Line"
    )
    l10n_ro_invoice_id = fields.Many2one("account.move", string="Romania - Invoice")
    l10n_ro_account_id = fields.Many2one(
        "account.account",
        compute="_compute_account",
        store=True,
        string="Romania - Valuation Account",
    )

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
            if svl.value > 0 and loc_dest.l10n_ro_property_stock_valuation_account_id:
                account = loc_dest.l10n_ro_property_stock_valuation_account_id
            if svl.value < 0 and loc_scr.l10n_ro_property_stock_valuation_account_id:
                account = loc_scr.l10n_ro_property_stock_valuation_account_id
            if svl.account_move_id:
                for aml in svl.account_move_id.line_ids.sorted(
                    lambda l: l.account_id.code
                ):
                    if aml.account_id.code[0] in ["2", "3"]:
                        if round(aml.balance, 2) == round(svl.value, 2):
                            account = aml.account_id
                            break
                        # if aml.balance <= 0 and svl.value <= 0:
                        #     account = aml.account_id
                        #     break
                        # if aml.balance > 0 and svl.value > 0:
                        #     account = aml.account_id
                        #     break
            if (
                svl.l10n_ro_valued_type in ("reception", "reception_return")
                and svl.l10n_ro_invoice_line_id
            ):
                account = svl.l10n_ro_invoice_line_id.account_id
            svl.l10n_ro_account_id = account

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if self.env["res.company"]._check_is_l10n_ro_record(
                values.get("company_id")
            ):
                if (
                    "l10n_ro_valued_type" not in values
                    and "stock_valuation_layer_id" in values
                ):
                    svl = self.env["stock.valuation.layer"].browse(
                        values["stock_valuation_layer_id"]
                    )
                    if svl:
                        values["l10n_ro_valued_type"] = svl.l10n_ro_valued_type
        return super(StockValuationLayer, self).create(vals_list)

    def _l10n_ro_compute_invoice_line_id(self):
        for svl in self:
            invoice_lines = self.env["account.move.line"]
            stock_move = svl.stock_move_id
            if not svl.l10n_ro_valued_type:
                continue
            if "reception" in svl.l10n_ro_valued_type:
                invoice_lines = stock_move.purchase_line_id.invoice_lines
            if "delivery" in svl.l10n_ro_valued_type:
                invoice_lines = stock_move.sale_line_id.invoice_lines

            if len(invoice_lines) == 1:
                svl.l10n_ro_invoice_line_id = invoice_lines
                svl.l10n_ro_invoice_id = invoice_lines.move_id
            else:
                for line in invoice_lines:
                    if stock_move.date.date() == line.move_id.date:
                        svl.l10n_ro_invoice_line_id = line
                        svl.l10n_ro_invoice_id = line.move_id
