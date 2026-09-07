# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockQuant(models.Model):
    _inherit = "stock.quant"

    l10n_ro_retail_markup_value = fields.Monetary(
        string="Markup (378)",
        compute="_compute_l10n_ro_retail_values",
        currency_field="currency_id",
        groups="stock.group_stock_manager",
    )
    l10n_ro_retail_vat_value = fields.Monetary(
        string="Deferred VAT (4428)",
        compute="_compute_l10n_ro_retail_values",
        currency_field="currency_id",
        groups="stock.group_stock_manager",
    )
    l10n_ro_retail_value = fields.Monetary(
        string="Retail Value (371)",
        compute="_compute_l10n_ro_retail_values",
        currency_field="currency_id",
        groups="stock.group_stock_manager",
        help="Cost plus the markup and deferred VAT actually loaded on this "
        "stock - what account 371 carries for it.",
    )

    @api.depends("quantity", "value", "location_id", "product_id")
    def _compute_l10n_ro_retail_values(self):
        """Split what account 371 carries for goods held in a shop.

        ``value`` keeps its core meaning - the cost - so the native valuation
        reports go on saying the same thing they say everywhere else. The
        retail figure is published next to it instead of replacing it: goods in
        a shop are carried at shelf price, and a report that silently returned
        the shelf price where every other module expects cost would be a
        divergence nobody could see.

        The markup comes from the ledger, not from today's pricelist, so this
        is what is really on 378 and 4428 - and the gap against the current
        shelf price is exactly what a price change document has to settle.
        """
        Ledger = self.env["l10n.ro.retail.markup.line"]
        self.l10n_ro_retail_markup_value = 0.0
        self.l10n_ro_retail_vat_value = 0.0
        for quant in self:
            quant.l10n_ro_retail_value = quant.value
            if not quant.location_id.l10n_ro_retail or not quant.product_id:
                continue
            company = quant.company_id or self.env.company
            warehouse = quant.location_id.warehouse_id
            if not warehouse:
                continue
            qty_on_hand = Ledger._l10n_ro_carried_qty(
                warehouse, quant.product_id, company
            )
            if float_is_zero(
                qty_on_hand, precision_rounding=quant.product_id.uom_id.rounding
            ):
                continue
            markup, vat = Ledger._l10n_ro_carried(warehouse, quant.product_id, company)
            share = quant.quantity / qty_on_hand
            currency = company.currency_id
            quant.l10n_ro_retail_markup_value = currency.round(markup * share)
            quant.l10n_ro_retail_vat_value = currency.round(vat * share)
            quant.l10n_ro_retail_value = currency.round(
                quant.value
                + quant.l10n_ro_retail_markup_value
                + quant.l10n_ro_retail_vat_value
            )
