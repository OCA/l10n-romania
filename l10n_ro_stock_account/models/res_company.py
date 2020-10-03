# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    romanian_accounting = fields.Boolean(string="Use Romanian accounting")

    property_stock_picking_payable_account_id = fields.Many2one(
        "account.account",
        string="Picking Account Payable",
        domain="[('internal_type', 'in', ['payable','other'])]",
        help="This account will be used as the payable account for the "
        "current partner on stock picking notice.",
    )
    property_stock_picking_receivable_account_id = fields.Many2one(
        "account.account",
        string="Picking Account Receivable",
        domain="[('internal_type', 'in', ['receivable','other'])]",
        help="This account will be used as the receivable account for the "
        "current partner on stock picking notice.",
    )
