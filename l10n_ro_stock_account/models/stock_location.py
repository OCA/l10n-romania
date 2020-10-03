# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockLlocation(models.Model):
    _inherit = "stock.location"

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

    # se va folosi   pentru a evalua diferit un produs care se
    # gaseste in aceasta locatie

    property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        string="Stock Valuation Account",
        company_dependent=True,
        domain="[('company_id', '=', current_company_id),"
        "('deprecated', '=', False)]",
    )
