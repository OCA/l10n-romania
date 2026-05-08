# Copyright 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("currency_id", "invoice_date", "invoice_currency_rate")
    def _onchange_currency_rate_to_invoice_line(self):
        if self.company_id.country_id.code != "RO":
            return

        # Apply only when SO currency differs from invoice currency
        sale_lines = self.invoice_line_ids.mapped("sale_line_ids")
        if not sale_lines:
            return
        so_currency = sale_lines[0].order_id.currency_id
        if not so_currency or so_currency == self.currency_id:
            return

        rate = self.invoice_currency_rate
        if not rate or rate <= 0:
            return

        for line in self.invoice_line_ids:
            so_line = line.sale_line_ids and line.sale_line_ids[0]

            if so_line and so_line.is_downpayment:
                # For downpayment deduction lines, use the price from the original
                # downpayment invoice so the amount exactly offsets what was billed.
                orig_lines = so_line.invoice_lines.filtered(
                    lambda lin: lin.move_id.state == "posted"
                    and lin.move_id != self._origin
                )
                if orig_lines:
                    orig = orig_lines[0]
                    orig_currency = orig.move_id.currency_id
                    if orig_currency == self.currency_id:
                        new_price = orig.price_unit
                    else:
                        new_price = orig_currency._convert(
                            orig.price_unit,
                            self.currency_id,
                            self.company_id,
                            orig.move_id.invoice_date or fields.Date.today(),
                        )
                else:
                    new_price = (line._origin.price_unit or line.price_unit) * rate
            else:
                base_price = (
                    so_line.price_unit
                    if so_line
                    else (line._origin.price_unit or line.price_unit)
                )
                new_price = base_price * rate

            if abs(line.price_unit - new_price) > 0.0001:
                line.price_unit = new_price
                line.tax_ids = line.tax_ids

        if hasattr(self, "_sync_dynamic_lines"):
            self._sync_dynamic_lines(container={"records": self})
