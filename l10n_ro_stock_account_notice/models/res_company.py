# Copyright (C) 2022 Dakai Soft
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

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
    property_notice_position_id = fields.Many2one('account.fiscal.position',
        domain="[('company_id', '=', current_company_id)]",
        ondelete="restrict",
        string=_("Fiscal position for notice picking"),
        help="Map tax and accounts on picking with notice. ")
    property_notice_include_vat = fields.Boolean(_("VAT in Piking"))


