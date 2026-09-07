# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class PriceDifferenceItem(models.TransientModel):
    _inherit = "l10n_ro.price_difference_item"

    l10n_ro_retail_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Shop",
        compute="_compute_l10n_ro_retail",
        help="The retail warehouse holding these goods, if any.",
    )
    l10n_ro_retail_markup = fields.Monetary(
        string="Markup Now",
        compute="_compute_l10n_ro_retail",
        currency_field="currency_id",
        help="Markup the goods in the shop carry on 378 today.",
    )
    l10n_ro_retail_markup_after = fields.Monetary(
        string="Markup After",
        compute="_compute_l10n_ro_retail",
        currency_field="currency_id",
        help="What the markup becomes once this price difference is absorbed. "
        "The shelf price does not move, so the difference comes out of here.",
    )
    l10n_ro_retail_covered = fields.Selection(
        [
            ("na", "Not in a shop"),
            ("ok", "Covered"),
            ("short", "Below cost"),
        ],
        string="Shelf Price",
        compute="_compute_l10n_ro_retail",
        help="Whether the shelf price still covers the cost after the "
        "difference. 'Below cost' means a price change is due first.",
    )

    @api.depends("stock_move_id", "value_diff", "product_id")
    def _compute_l10n_ro_retail(self):
        """Say what the difference does to the markup, before it is posted.

        The difference is absorbed by 378, not by 371 - the shelf price does
        not move because a supplier invoiced more. Showing the markup that is
        left turns the confirmation into a decision: post it, or raise the
        shelf price first with a Proces Verbal.
        """
        Ledger = self.env["l10n.ro.retail.markup.line"]
        for item in self:
            item.l10n_ro_retail_warehouse_id = False
            item.l10n_ro_retail_markup = 0.0
            item.l10n_ro_retail_markup_after = 0.0
            item.l10n_ro_retail_covered = "na"
            move = item.stock_move_id
            if not move or not move.location_dest_id.l10n_ro_retail:
                continue
            warehouse = move.location_dest_id.warehouse_id
            company = move.company_id or self.env.company
            markup, _vat = Ledger._l10n_ro_carried(warehouse, item.product_id, company)
            after = markup - item.value_diff
            item.l10n_ro_retail_warehouse_id = warehouse
            item.l10n_ro_retail_markup = markup
            item.l10n_ro_retail_markup_after = after
            item.l10n_ro_retail_covered = (
                "ok"
                if float_compare(
                    after, 0.0, precision_rounding=company.currency_id.rounding
                )
                >= 0
                else "short"
            )
