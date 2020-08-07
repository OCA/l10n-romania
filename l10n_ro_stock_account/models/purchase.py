# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_account_move_line(self, move=False):
        """
        Modify the account if this invoice is for a reception with notice.
        Is setting account 408 ' Furnizori - facturi nesosite' that must be
        used if the goods where received with notice/aviz before the invoice
        """
        data = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        prod = self.product_id
        payable_acc = self.company_id.property_stock_picking_payable_account_id.id
        prod_acc = prod.product_tmpl_id.get_product_accounts()["stock_valuation"]
        # Overwrite with the incoming location valuation in
        stock_move = self.move_ids and self.move_ids[0] or None
        if stock_move and stock_move.location_dest_id.valuation_in_account_id:
            prod_acc = stock_move.location_dest_id.valuation_in_account_id.id
        if prod.purchase_method == "receive":
            # Control bills based on received quantities
            if prod.type == "product":
                if any([picking.notice for picking in self.order_id.picking_ids]):
                    # if exist at least one notice/aviz we are going to make
                    # at reception accounting lines with 408
                    # even if the invoice came the same day as reception;
                    # we are going to have a debit and a credit in account 408
                    # so is the same as making only accounting lines on
                    # invoice
                    data["account_id"] = payable_acc
                else:
                    data["account_id"] = prod_acc
        else:
            # Control bills based on ordered quantities
            if self.product_id.type == "product":
                data["account_id"] = prod_acc
        return data
