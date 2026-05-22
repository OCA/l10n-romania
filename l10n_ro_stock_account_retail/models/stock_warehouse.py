# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    l10n_ro_retail = fields.Boolean(
        string="Retail Warehouse (Marfa in Magazin)",
        help="Mark this warehouse as retail. Goods in its internal locations "
        "are valued at retail price (PVA) on account 371, with the markup "
        "booked on 378 and the deferred VAT on 4428.",
    )
    l10n_ro_retail_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Retail Pricelist",
        check_company=True,
        help="Pricelist used to determine the retail price (PVA) for "
        "products in this warehouse. The price is interpreted through the "
        "product taxes to split it between markup (378) and deferred VAT "
        "(4428). If empty, product.list_price is used.",
    )
