# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange("type")
    def _onchange_type(self):
        """ Force values to stay consistent with integrity constraints """
        res = super(ProductTemplate, self)._onchange_type()
        if self.type == "service":
            # Update taxes with the default service taxes defined in company
            if self.env.company.account_serv_sale_tax_id:
                res["taxes_id"] = self.env.company.account_serv_sale_tax_id
            if self.env.company.account_serv_purchase_tax_id:
                res["supplier_taxes_id"] = self.env.company.account_serv_purchase_tax_id
        return res
