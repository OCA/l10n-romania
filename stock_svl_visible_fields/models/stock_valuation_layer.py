# Copyright (C) 2022 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).


from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    stock_valuation_layer_id_id = fields.Integer(
        string="Linked to ID", related="stock_valuation_layer_id.id", store=1
    )
    stock_move_state = fields.Selection(
        string="Stock Move Status", related="stock_move_id.state", readonly=1
    )
    account_move_state = fields.Selection(
        string="Journal Entry Status", related="account_move_id.state", readonly=1
    )
    # should not exist becuase l10n_ro_invoice_id should not be used. but account_move_id
    # invoice_state = fields.Selection(
        # string="Invoice Status", related="l10n_ro_invoice_id.state", readonly=1
    # )
