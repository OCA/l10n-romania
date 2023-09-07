# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class StockLocation(models.Model):
    _inherit = "stock.location"

    l10n_ro_property_account_income_location_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Romania - Income Account",
        domain="['&', ('deprecated', '=', False),"
        "('company_id', '=', current_company_id)]",
        help="This account will overwrite the income accounts from product "
        "or category.",
    )
    l10n_ro_property_account_expense_location_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Romania - Expense Account",
        domain="['&', ('deprecated', '=', False),"
        "('company_id', '=', current_company_id)]",
        help="This account will overwrite the expense accounts from product "
        "or category.",
    )

    # se va folosi   pentru a evalua diferit un produs care se
    # gaseste in aceasta locatie

    l10n_ro_property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        string="Romania - Stock Valuation Account",
        company_dependent=True,
        domain="[('company_id', '=', current_company_id),"
        "('deprecated', '=', False)]",
    )

    l10n_ro_accounting_location = fields.Boolean(
        string="Is Accounting Location",
        help="Only for Romania, this define a category " "as accounting location",
    )
    l10n_ro_accounting_location_id = fields.Many2one(
        "stock.location",
        string="Parent Accounting Location",
        help="Only for Romania, link a location " "on accounting location",
    )

    def _l10n_ro_prepare_copy_values(self, values):
        for value in values:
            if value.get("l10n_ro_accounting_category_id", None):
                value.update(self._l10n_ro_prepare_copy_value(value))
        return values

    def _l10n_ro_prepare_copy_value(self, value):
        accouning_category = self.browse(value.get("l10n_ro_accounting_location_id"))
        return accouning_category._l10n_ro_copy_value(value)

    def _l10n_ro_copy_value(self, value={}):
        value.update(
            {
                "l10n_ro_property_account_income_location_id": (
                    self.l10n_ro_property_account_income_location_id.id
                ),
                "l10n_ro_property_account_expense_location_id": (
                    self.l10n_ro_property_account_expense_location_id.id
                ),
                "l10n_ro_property_stock_valuation_account_id": (
                    self.l10n_ro_property_stock_valuation_account_id.id
                ),
            }
        )
        return value

    def _l10n_ro_check_value_is_different(self, value):
        value2 = self._l10n_ro_copy_value()
        res = False
        for key, val in value.items():
            if value2.get(key) != val:
                res = True
                break
        return res

    def _l10n_ro_pushStockLocation_accounting(self):
        for s in self:
            value = s._l10n_ro_copy_value()
            self.search([("l10n_ro_accounting_location_id", "=", s.id)]).write(value)

    def write(self, value):
        if ('l10n_ro_accounting_location' in value
            and not self.env.user.has_group('account.group_account_manager')
            ):
            raise UserError("Non-Accountant User have no access on this field")

        if value.get("l10n_ro_accounting_location_id", None):
            value = self._l10n_ro_prepare_copy_value(value)
        reset_accounting_location = self.filtered(
            lambda x: (
                x.l10n_ro_accounting_location
                and x._l10n_ro_check_value_is_different(value)
                )
        )
        res = super(StockLocation, self).write(value)
        if res and reset_accounting_location:
            reset_accounting_location._l10n_ro_pushStockLocation_accounting()
        return res

    @api.model_create_multi
    def create(self, values):
        values = self._l10n_ro_prepare_copy_values(values)
        return super(StockLocation, self).create(values)

