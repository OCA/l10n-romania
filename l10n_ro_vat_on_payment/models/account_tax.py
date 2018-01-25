# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # Taken from Odoo master
    cash_basis_base_account_id = fields.Many2one(
        'account.account',
        domain=[('deprecated', '=', False)],
        string='Base Tax Received Account',
        help='Account that will be set on lines created in cash basis journal'
             ' entry and used to keep track of the tax base amount.')
