# Copyright 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("currency_id", "invoice_date", "invoice_currency_rate")
    def _onchange_currency_rate_to_invoice_line(self):
        if self.company_id.country_id.code != "RO":
            return

        if self.invoice_line_ids.mapped("sale_line_ids"):
            repriced = self._l10n_ro_reprice_from_sale_order()
        else:
            repriced = self._l10n_ro_reprice_from_origin()

        if repriced and hasattr(self, "_sync_dynamic_lines"):
            self._sync_dynamic_lines(container={"records": self})

    def _l10n_ro_reprice_from_sale_order(self):
        """Reprice the lines of an invoice that comes from a sale order.

        Returns whether the lines were repriced at all.
        """
        sale_lines = self.invoice_line_ids.mapped("sale_line_ids")
        so_currency = sale_lines[0].order_id.currency_id
        if not so_currency:
            return False

        reverting_to_so_currency = so_currency == self.currency_id
        rate = self.invoice_currency_rate
        if not reverting_to_so_currency and (not rate or rate <= 0):
            return False

        for line in self.invoice_line_ids:
            so_line = line.sale_line_ids and line.sale_line_ids[0]
            if so_line and so_line.is_downpayment:
                new_price = self._l10n_ro_downpayment_price(
                    line, so_line, reverting_to_so_currency, rate
                )
            else:
                base_price = self._l10n_ro_base_price(line, so_line)
                new_price = (
                    base_price if reverting_to_so_currency else base_price * rate
                )
            self._l10n_ro_set_price(line, new_price)
        return True

    def _l10n_ro_downpayment_price(self, line, so_line, reverting, rate):
        """Price of a downpayment line.

        A deduction line in the final invoice has to offset exactly what the
        posted downpayment invoice already billed, so it follows that invoice
        rather than the rate typed here. The downpayment invoice itself has no
        such predecessor and is priced from the sale order.
        """
        orig_lines = so_line.invoice_lines.filtered(
            lambda lin: lin.move_id.state == "posted" and lin.move_id != self._origin
        )
        if not orig_lines:
            base_price = self._l10n_ro_base_price(line, so_line)
            return base_price if reverting else base_price * rate

        orig = orig_lines[0]
        orig_currency = orig.move_id.currency_id
        if orig_currency == self.currency_id:
            return orig.price_unit
        return orig_currency._convert(
            orig.price_unit,
            self.currency_id,
            self.company_id,
            orig.move_id.invoice_date or fields.Date.today(),
        )

    def _l10n_ro_reprice_from_origin(self):
        """Reprice the lines of an invoice that has no sale order behind it.

        The original price is taken back to the company currency and out again
        at the invoice rate. Returns whether the lines were repriced at all.
        """
        company_currency = self.company_id.currency_id
        orig_currency = self._origin.currency_id or company_currency
        orig_rate = self._origin.invoice_currency_rate or 1.0
        reverting_to_orig_currency = orig_currency == self.currency_id

        rate = self.invoice_currency_rate
        if not reverting_to_orig_currency and (not rate or rate <= 0):
            return False

        for line in self.invoice_line_ids:
            orig_price = line._origin.price_unit or line.price_unit
            if not orig_price:
                continue

            if reverting_to_orig_currency:
                new_price = orig_price
            else:
                price_in_company = (
                    orig_price
                    if orig_currency == company_currency
                    else orig_price / orig_rate
                )
                new_price = (
                    price_in_company
                    if self.currency_id == company_currency
                    else price_in_company * rate
                )
            self._l10n_ro_set_price(line, new_price)
        return True

    def _l10n_ro_base_price(self, line, so_line):
        """Price to start from: the sale order line when there is one, else
        what the invoice line held before this onchange."""
        if so_line:
            return so_line.price_unit
        return line._origin.price_unit or line.price_unit

    def _l10n_ro_set_price(self, line, new_price):
        if abs(line.price_unit - new_price) > 0.0001:
            line.price_unit = new_price
            line.tax_ids = line.tax_ids
