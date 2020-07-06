# ©  2008-2018 Fekete Mihai <mihai.fekete@forbiom.eu>
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import _, api, fields, models


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = "stock.valuation.layer.revaluation"

    @api.model
    def default_get(self, fields_list):
        res = super(StockValuationLayerRevaluation, self).default_get(fields_list)
        product_id = self.product_id
        if "account_id" in fields_list:
            res["account_id"] = (
                product_or_template.property_account_creditor_price_difference.id
                or product_or_template.categ_id.property_account_creditor_price_difference_categ.id
            )
        return res


#     # in metoda standard se foloseste active_id si se aduce un id gresit
#     # oare mai este necesar in 13 ?
#     def change_price(self):
#         """ Changes the Standard Price of Product and creates an account move accordingly. """
#         self.ensure_one()
#         if self._context['active_model'] == 'product.template':
#             products = self.env['product.template'].browse(self._context['active_ids']).product_variant_ids
#         else:
#             products = self.env['product.product'].browse(self._context['active_ids'])
#
#         products._change_standard_price(self.new_price, self.counterpart_account_id.id)
#         return {'type': 'ir.actions.act_window_close'}
