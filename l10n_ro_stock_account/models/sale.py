# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self):
        """
        Modify the account if this invoice is for a notice/aviz
        stock movement that happened before
        Is setting account 418 that must be used if the goods
        where sent before the invoice
        account 418 must be != receivable
        if not it can not be put into invoice and also the base
        is wrong at computing taxes
        """
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        company = self.company_id
        # Overwrite with at least one location with income account defined
        for picking in self.order_id.picking_ids:
            moves = picking.move_line_ids.filtered(lambda m: m.state == "done")
            for move in moves:
                if move.location_id.property_account_income_location_id:
                    res[
                        "account_id"
                    ] = move.location_id.property_account_income_location_id
                    break
        if self.product_id.invoice_policy == "delivery":
            if any([picking.notice for picking in self.order_id.picking_ids]):
                res[
                    "account_id"
                ] = company.property_stock_picking_receivable_account_id.id
        return res
