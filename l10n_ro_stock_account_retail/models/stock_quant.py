from odoo import models, tools


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _compute_value(self):
        res = super()._compute_value()

        retail_quants = self.filtered(lambda q: q.location_id.l10n_ro_retail)
        for rec in retail_quants:
            company = rec.company_id or self.env.company
            currency = company.currency_id
            prices = (
                rec.product_id.product_tmpl_id._l10n_ro_get_retail_prices(
                    warehouse=rec.warehouse_id, company=company
                )
                if rec.product_id
                else {"price_without_vat": 0.0, "price_with_vat": 0.0, "vat": 0.0}
            )
            rec.value = tools.float_round(
                prices["price_with_vat"] * rec.quantity,
                precision_rounding=currency.rounding,
            )
        return res
