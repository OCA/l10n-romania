# Copyright 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_downpayment_line_price_unit(self, invoices):
        company = self.company_id or self.env.company
        if company.country_id.code != "RO":
            return super()._get_downpayment_line_price_unit(invoices)

        so_currency = self.order_id.currency_id
        total = 0.0
        for inv_line in self.invoice_lines:
            if inv_line.move_id.state != "posted" or inv_line.move_id in invoices:
                continue
            sign = 1 if inv_line.move_id.move_type == "out_invoice" else -1
            price = sign * inv_line.price_unit
            inv_currency = inv_line.move_id.currency_id
            # Only convert when invoice currency differs from SO currency
            if inv_currency and inv_currency != so_currency:
                price = inv_currency._convert(
                    price,
                    so_currency,
                    company,
                    inv_line.move_id.invoice_date or fields.Date.today(),
                )
            total += price
        return total
