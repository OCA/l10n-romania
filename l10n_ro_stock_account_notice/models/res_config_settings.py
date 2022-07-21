# Copyright (C) 2022 Dakai Soft
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

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

    property_notice_position_id = fields.Many2one(
        "account.fiscal.position",
        related="company_id.property_notice_position_id",
        readonly=False,
    )
    property_notice_include_vat = fields.Boolean(
        related="company_id.property_notice_include_vat", 
        readonly=False,
        )
