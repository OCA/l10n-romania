# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools


class StockRetailReport(models.Model):
    _name = "l10n.ro.stock.retail.report"
    _description = "Retail stock report (Marfa in magazin)"
    _auto = False
    _order = "warehouse_id, product_id"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse", readonly=True)
    location_id = fields.Many2one("stock.location", string="Location", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    product_tmpl_id = fields.Many2one(
        "product.template", string="Product Template", readonly=True
    )
    categ_id = fields.Many2one("product.category", string="Category", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    quantity = fields.Float(readonly=True)
    cost_unit = fields.Float(
        string="Cost / Unit", compute="_compute_values", store=False
    )
    cost_total = fields.Float(string="Cost Total", compute="_compute_values")
    price_no_vat_unit = fields.Float(
        string="Retail Price / Unit (ex VAT)", compute="_compute_values"
    )
    price_with_vat_unit = fields.Float(
        string="Retail Price / Unit (incl VAT)", compute="_compute_values"
    )
    markup_unit = fields.Float(string="Markup / Unit (378)", compute="_compute_values")
    vat_unit = fields.Float(
        string="Deferred VAT / Unit (4428)", compute="_compute_values"
    )
    markup_total = fields.Float(
        string="Markup Total (378)", compute="_compute_values"
    )
    vat_total = fields.Float(
        string="Deferred VAT Total (4428)", compute="_compute_values"
    )
    retail_value = fields.Float(
        string="Retail Value (371)", compute="_compute_values"
    )

    @property
    def _table_query(self):
        return """
            SELECT
                row_number() OVER () AS id,
                sq.company_id AS company_id,
                sl.warehouse_id AS warehouse_id,
                sq.location_id AS location_id,
                sq.product_id AS product_id,
                pp.product_tmpl_id AS product_tmpl_id,
                pt.categ_id AS categ_id,
                SUM(sq.quantity) AS quantity
            FROM stock_quant sq
            JOIN stock_location sl ON sl.id = sq.location_id
            JOIN product_product pp ON pp.id = sq.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            JOIN stock_warehouse sw ON sw.id = sl.warehouse_id
            WHERE sl.usage = 'internal'
              AND sl.l10n_ro_retail = TRUE
              AND sw.l10n_ro_retail = TRUE
              AND sq.quantity > 0
            GROUP BY sq.company_id, sl.warehouse_id, sq.location_id,
                     sq.product_id, pp.product_tmpl_id, pt.categ_id
        """

    @api.depends("product_id", "warehouse_id", "company_id", "quantity")
    def _compute_values(self):
        for rec in self:
            company = rec.company_id or self.env.company
            currency = company.currency_id
            cost_unit = (
                rec.product_id.with_company(company).standard_price
                if rec.product_id
                else 0.0
            )
            prices = (
                rec.product_id.product_tmpl_id._l10n_ro_get_retail_prices(
                    warehouse=rec.warehouse_id, company=company
                )
                if rec.product_id
                else {"price_without_vat": 0.0, "price_with_vat": 0.0, "vat": 0.0}
            )
            markup_unit = prices["price_without_vat"] - cost_unit
            vat_unit = prices["vat"]
            qty = rec.quantity or 0.0
            rec.cost_unit = cost_unit
            rec.cost_total = tools.float_round(
                cost_unit * qty, precision_rounding=currency.rounding
            )
            rec.price_no_vat_unit = prices["price_without_vat"]
            rec.price_with_vat_unit = prices["price_with_vat"]
            rec.markup_unit = markup_unit
            rec.vat_unit = vat_unit
            rec.markup_total = tools.float_round(
                markup_unit * qty, precision_rounding=currency.rounding
            )
            rec.vat_total = tools.float_round(
                vat_unit * qty, precision_rounding=currency.rounding
            )
            rec.retail_value = tools.float_round(
                prices["price_with_vat"] * qty,
                precision_rounding=currency.rounding,
            )
