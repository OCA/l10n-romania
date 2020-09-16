# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        invoice_vals["intrastat_country_id"] = (
            self.partner_shipping_id.country_id.id
            or self.partner_id.country_id.id
            or self.partner_invoice_id.country_id.id
        )

        return invoice_vals
