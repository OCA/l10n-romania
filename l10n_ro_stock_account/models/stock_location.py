# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class stock_location(models.Model):
    _inherit = "stock.location"

    property_account_creditor_price_difference_location_id = fields.Many2one(
        "account.account",
        string="Price Difference Account",
        help="This account will be used to value price "
        "difference between purchase price and cost price.",
    )
    property_account_income_location_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Income Account",
        domain="['&', ('deprecated', '=', False),"
        "('company_id', '=', current_company_id)]",
        help="This account will overwrite the income accounts from product "
        "or category.",
    )
    property_account_expense_location_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Expense Account",
        domain="['&', ('deprecated', '=', False),"
        "('company_id', '=', current_company_id)]",
        help="This account will overwrite the expense accounts from product "
        "or category.",
    )
