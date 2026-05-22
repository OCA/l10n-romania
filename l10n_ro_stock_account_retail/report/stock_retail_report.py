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
    cost_unit = fields.Float(string="Cost / Unit", readonly=True)
    cost_total = fields.Float(string="Cost Total", readonly=True)
    price_no_vat_unit = fields.Float(
        string="Retail Price / Unit (ex VAT)", readonly=True
    )
    price_with_vat_unit = fields.Float(
        string="Retail Price / Unit (incl VAT)", readonly=True
    )
    markup_unit = fields.Float(string="Markup / Unit (378)", readonly=True)
    vat_unit = fields.Float(string="Deferred VAT / Unit (4428)", readonly=True)
    markup_total = fields.Float(string="Markup Total (378)", readonly=True)
    vat_total = fields.Float(string="Deferred VAT Total (4428)", readonly=True)
    retail_value = fields.Float(string="Retail Value (371)", readonly=True)

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
                SUM(sq.quantity) AS quantity,
                MAX(sq.value / NULLIF(sq.quantity, 0)) AS cost_unit,
                SUM(sq.value) AS cost_total,
                0.0::numeric AS price_no_vat_unit,
                0.0::numeric AS price_with_vat_unit,
                0.0::numeric AS markup_unit,
                0.0::numeric AS vat_unit,
                0.0::numeric AS markup_total,
                0.0::numeric AS vat_total,
                0.0::numeric AS retail_value
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

    @api.depends_context("company")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.warehouse_id.display_name or ''} - "
                f"{rec.product_id.display_name or ''}"
            )

    def read(self, fields_to_read=None, load="_classic_read"):
        """Enrich the recordset with the live retail prices (which depend
        on the warehouse pricelist and product taxes — too dynamic to
        compute in SQL)."""
        records = super().read(fields_to_read=fields_to_read, load=load)
        if not records:
            return records
        recs_by_id = {r["id"]: r for r in records}
        recordset = self.browse(list(recs_by_id))
        for rec in recordset:
            data = recs_by_id[rec.id]
            warehouse = rec.warehouse_id
            company = rec.company_id or self.env.company
            prices = rec.product_id.product_tmpl_id._l10n_ro_get_retail_prices(
                warehouse=warehouse, company=company
            )
            markup_unit = prices["price_without_vat"] - (data.get("cost_unit") or 0.0)
            vat_unit = prices["vat"]
            qty = data.get("quantity") or 0.0
            if "price_no_vat_unit" in data:
                data["price_no_vat_unit"] = prices["price_without_vat"]
            if "price_with_vat_unit" in data:
                data["price_with_vat_unit"] = prices["price_with_vat"]
            if "markup_unit" in data:
                data["markup_unit"] = markup_unit
            if "vat_unit" in data:
                data["vat_unit"] = vat_unit
            if "markup_total" in data:
                data["markup_total"] = tools.float_round(
                    markup_unit * qty,
                    precision_rounding=company.currency_id.rounding,
                )
            if "vat_total" in data:
                data["vat_total"] = tools.float_round(
                    vat_unit * qty,
                    precision_rounding=company.currency_id.rounding,
                )
            if "retail_value" in data:
                data["retail_value"] = tools.float_round(
                    prices["price_with_vat"] * qty,
                    precision_rounding=company.currency_id.rounding,
                )
        return records
