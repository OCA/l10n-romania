# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from psycopg2 import sql

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
    value_total = fields.Float(
        string="Stock Value (cost)",
        readonly=True,
        help="On-hand cost value at the requested date (from stock.valuation.layer).",
    )
    cost_unit = fields.Float(
        string="Cost / Unit", compute="_compute_values", store=False
    )
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
    markup_total = fields.Float(string="Markup Total (378)", compute="_compute_values")
    vat_total = fields.Float(
        string="Deferred VAT Total (4428)", compute="_compute_values"
    )
    retail_value = fields.Float(string="Retail Value (371)", compute="_compute_values")

    @property
    def _table_query(self):
        # at_date may be a datetime, a date, a string, or None
        raw = self.env.context.get("l10n_ro_retail_at_date")
        if raw:
            at_date = fields.Datetime.to_string(fields.Datetime.to_datetime(raw))
            date_clause = sql.SQL("sm.date <= {}").format(sql.Literal(at_date))
        else:
            date_clause = sql.SQL("TRUE")
        query = sql.SQL(
            """
            WITH retail_legs AS (
                -- inbound to a retail location (counts +qty / +value)
                SELECT
                    sm.product_id,
                    sm.company_id,
                    sld.warehouse_id AS warehouse_id,
                    sld.id AS location_id,
                    sm.product_qty AS qty,
                    sm.value AS value
                FROM stock_move sm
                JOIN stock_location sld ON sld.id = sm.location_dest_id
                JOIN stock_warehouse sw ON sw.id = sld.warehouse_id
                WHERE sm.state = 'done'
                  AND {date_clause}
                  AND sld.usage = 'internal'
                  AND sld.l10n_ro_retail = TRUE
                  AND sw.l10n_ro_retail = TRUE
                UNION ALL
                -- outbound from a retail location (counts -qty / -value)
                SELECT
                    sm.product_id,
                    sm.company_id,
                    sls.warehouse_id AS warehouse_id,
                    sls.id AS location_id,
                    -sm.product_qty AS qty,
                    -sm.value AS value
                FROM stock_move sm
                JOIN stock_location sls ON sls.id = sm.location_id
                JOIN stock_warehouse sw ON sw.id = sls.warehouse_id
                WHERE sm.state = 'done'
                  AND {date_clause}
                  AND sls.usage = 'internal'
                  AND sls.l10n_ro_retail = TRUE
                  AND sw.l10n_ro_retail = TRUE
            )
            SELECT
                (rl.warehouse_id * 100000000
                    + rl.location_id * 1000000
                    + rl.product_id) AS id,
                rl.company_id AS company_id,
                rl.warehouse_id AS warehouse_id,
                rl.location_id AS location_id,
                rl.product_id AS product_id,
                pp.product_tmpl_id AS product_tmpl_id,
                pt.categ_id AS categ_id,
                SUM(rl.qty)::numeric AS quantity,
                SUM(rl.value)::numeric AS value_total
            FROM retail_legs rl
            JOIN product_product pp ON pp.id = rl.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            GROUP BY rl.company_id, rl.warehouse_id, rl.location_id,
                     rl.product_id, pp.product_tmpl_id, pt.categ_id
            HAVING SUM(rl.qty) > 0
            """
        ).format(date_clause=date_clause)
        return query.as_string(self.env.cr._cnx)

    @api.depends("product_id", "warehouse_id", "company_id", "quantity", "value_total")
    def _compute_values(self):
        for rec in self:
            company = rec.company_id or self.env.company
            currency = company.currency_id
            qty = rec.quantity or 0.0
            cost_unit = (rec.value_total / qty) if qty else 0.0
            prices = (
                rec.product_id.product_tmpl_id._l10n_ro_get_retail_prices(
                    warehouse=rec.warehouse_id, company=company
                )
                if rec.product_id
                else {"price_without_vat": 0.0, "price_with_vat": 0.0, "vat": 0.0}
            )
            markup_unit = prices["price_without_vat"] - cost_unit
            vat_unit = prices["vat"]
            rec.cost_unit = cost_unit
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
