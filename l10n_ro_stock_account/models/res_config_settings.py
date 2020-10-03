# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # stock section
    use_anglo_saxon = fields.Boolean(
        string="Anglo-Saxon Accounting",
        related="company_id.anglo_saxon_accounting",
        readonly=False,
    )

    use_romanian_accounting = fields.Boolean(
        string="Romanian Accounting",
        related="company_id.romanian_accounting",
        readonly=False,
    )

    property_stock_picking_payable_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_picking_payable_account_id",
        readonly=False,
    )
    property_stock_picking_receivable_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_picking_receivable_account_id",
        readonly=False,
    )
