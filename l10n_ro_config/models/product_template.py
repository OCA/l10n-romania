# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    @api.onchange("type")
    def _onchange_type(self):
        # Update service products with the default service
        # taxes defined in company
        res = super(ProductTemplate, self)._onchange_type()
        if self.type == "service" and self.is_l10n_ro_record:
            company = self.company_id or self.env.company
            if company.l10n_ro_account_serv_sale_tax_id:
                self.taxes_id = company.l10n_ro_account_serv_sale_tax_id
            if company.l10n_ro_account_serv_purchase_tax_id:
                self.supplier_taxes_id = company.l10n_ro_account_serv_purchase_tax_id
        return res
