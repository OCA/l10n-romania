# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    dvi_id = fields.Many2one("stock.landed.cost", string="DVI")

    def button_dvi(self):
        if self.dvi_id:
            # afisare DVI
            action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
            action = action.read()[0]
            action["views"] = [(False, "form")]
            action["res_id"] = self.dvi_id.id
        else:
            # generare dvi
            action = self.env.ref("l10n_ro_dvi.action_account_invoice_dvi")
            action = action.read()[0]

        return action
