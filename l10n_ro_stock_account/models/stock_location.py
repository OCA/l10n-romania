# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class StockLocation(models.Model):
    _inherit = "stock.location"

    l10n_ro_property_account_income_location_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will overwrite the income accounts from product "
        "or category.",
    )
    l10n_ro_property_account_expense_location_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will overwrite the expense accounts from product "
        "or category.",
    )

    l10n_ro_property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        string="Stock Valuation Account Romania",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
    )

    def propagate_account(self):
        for location in self:
            children = self.search([("id", "child_of", [location.id])])
            if not children:
                continue
            values = {
                "l10n_ro_property_account_income_location_id": location.l10n_ro_property_account_income_location_id.id,  # noqa
                "l10n_ro_property_account_expense_location_id": location.l10n_ro_property_account_expense_location_id.id,  # noqa
                "l10n_ro_property_stock_valuation_account_id": location.l10n_ro_property_stock_valuation_account_id.id,  # noqa
            }
            children.write(values)
