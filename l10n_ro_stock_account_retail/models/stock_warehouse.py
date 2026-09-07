# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    l10n_ro_retail = fields.Boolean(
        string="Retail Warehouse",
        help="Mark this warehouse as retail. Goods in its internal locations "
        "are valued at retail price (PVA) on account 371, with the markup "
        "booked on 378 and the deferred VAT on 4428.",
    )
    l10n_ro_retail_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Retail Pricelist",
        check_company=True,
        help="Pricelist holding the shelf price (PVA) of the products in this "
        "warehouse. Prices on a retail pricelist are always VAT included: it "
        "is the price on the shelf label, and the price account 371 carries. "
        "If empty, the product sale price is used.",
    )
    l10n_ro_retail_allow_negative_markup = fields.Boolean(
        string="Allow Selling Below Cost",
        help="By default a shelf price lower than the cost is refused, because "
        "it books a negative markup on 378 and almost always means the price "
        "or the cost is wrong. Tick this for a shop that legitimately sells "
        "below cost - clearance, perishables close to expiry, the cases in "
        "OG 99/2000 - where the negative markup is intended.",
    )
