# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


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
        string="Romania - Is Accounting Location",
        help="Only for Romania, this define a category "
        "as accounting location",
        )
    l10n_ro_accounting_location_id = fields.Many2one(
        string="Romania - Parent Accounting Location",
        help="Only for Romania, link a location "
        "on accounting location",
        )
    
    
    def _l10n_ro_prepare_copy_values(self, values):
        for value in values:
            if 'l10n_ro_accounting_category_id' in value:
                value.update(
                    self._l10n_ro_prepare_copy_value(value)
                    )
        return values
        
    def _l10n_ro_prepare_copy_value(self, value):
        accouning_category = self.browse(value.get('l10n_ro_accounting_location_id'))
        return accouning_category._l10n_ro_copy_value(value)
    
    def _l10n_ro_copy_value(self, value):
        value.update({
            'l10n_ro_property_account_income_location_id': self.l10n_ro_property_account_income_location_id.id,
            'l10n_ro_property_account_expense_location_id': self.l10n_ro_property_account_expense_location_id.id,
            'l10n_ro_property_stock_valuation_account_id': self.l10n_ro_property_stock_valuation_account_id.id,
            })
        return value
    
    @api.multi
    def write(self, value):
        if 'l10n_ro_accounting_location_id' in value:
            value = self._l10n_ro_prepare_copy_value(value)
        return super(StockLocation, self).write(value)
    
    @api.model
    def create(self, values):
        values = self._l10n_ro_prepare_copy_values(values)
        return super(StockLocation, self).create(values)
    
    @api.multi
    def l10n_ro_fixStockLocation_accounting(self):
        for s in self:
            value = s._l10n_ro_copy_value({})
            self.search([('l10n_ro_accounting_location_id','=',s.id)]).write(value)
