# Copyright (C) 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).


import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _name = "stock.quant"
    _inherit = ["stock.quant", "l10n.ro.mixin"]

    company_id = fields.Many2one(index=True)

    @api.depends(
        "company_id", "location_id", "owner_id", "product_id", "quantity", "lot_id"
    )
    # pylint: disable=W8110
    def _compute_value(self):
        ro_quants = self.filtered(
            lambda quant: quant.company_id.l10n_ro_accounting
            and quant.location_id.usage == "internal"
        )
        super(StockQuant, self - ro_quants)._compute_value()
        quants_without_lot_allocation = ro_quants.filtered(
            lambda q: not q.company_id.l10n_ro_stock_account_svl_lot_allocation
            and q.lot_id
        )
        products = quants_without_lot_allocation.mapped("product_id")
        locations = quants_without_lot_allocation.mapped("location_id")
        for product in products:
            for location in locations:
                quants = quants_without_lot_allocation.filtered(
                    lambda q: q.location_id == location and q.product_id == product
                ).sorted("in_date")
                svls = (
                    self.env["stock.valuation.layer"]
                    .search(
                        [
                            ("product_id", "=", product.id),
                            ("company_id", "=", location.company_id.id),
                            ("l10n_ro_location_dest_id", "=", location.id),
                            ("remaining_qty", ">", 0),
                        ]
                    )
                    .sorted("create_date")
                )
                svl_lots = set(svls.mapped("l10n_ro_lot_ids"))
                sq_lots = quants.filtered(lambda l: l.lot_id in svl_lots)
                svl_with_lot_in_sq_lot = svls.filtered(
                    lambda l: l.l10n_ro_lot_ids in sq_lots.mapped("lot_id")
                )
                for svl in svl_with_lot_in_sq_lot:
                    for sq in sq_lots:
                        if (
                            svl.remaining_qty == sq.quantity
                            and sq.lot_id in svl.l10n_ro_lot_ids
                        ):
                            quants -= sq
                            quants_without_lot_allocation -= sq
                            svls -= svl
                remaining_quant = quants
                remaining_svl = svls
                svl_list = [
                    {
                        "qty": svl.remaining_qty,
                        "price": svl.unit_cost,
                        "added_cost": sum(
                            [s.value for s in svl.stock_valuation_layer_ids]
                        ),
                    }
                    for svl in remaining_svl
                ]
                for quant in remaining_quant:
                    quant_quantity = quant.quantity
                    quant_value = 0
                    for svl in svl_list:
                        if quant_quantity > 0:
                            if svl["qty"] >= quant_quantity:
                                quant_value += (
                                    quant_quantity * svl["price"] + svl["added_cost"]
                                )
                                svl["qty"] -= quant_quantity
                                quant_quantity = 0
                            else:
                                quant_value += (
                                    svl["qty"] * svl["price"] + svl["added_cost"]
                                )
                                quant_quantity -= svl["qty"]
                                svl["qty"] = 0
                            if svl["qty"] <= 0:
                                svl_list.pop(0)
                        else:
                            break
                    quant.value = quant_value
                    quant.currency_id = quant.company_id.currency_id

        quants_with_loc = ro_quants - quants_without_lot_allocation
        for quant in quants_with_loc:
            quant = quant.with_context(
                location_id=quant.location_id.id,
                lot_id=quant.lot_id.id,
                force_svl_lot_config=True,
            )
            super(StockQuant, quant)._compute_value()
