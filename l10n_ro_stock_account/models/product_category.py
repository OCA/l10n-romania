# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _name = "product.category"
    _inherit = ["product.category", "l10n.ro.mixin"]

    l10n_ro_hide_stock_in_out_account = fields.Boolean(
        compute="_compute_hide_accounts",
        string="Romania - Hide Odoo Stock In/Out Accounts",
        help="Only for Romania, to hide stock_input and stock_output "
        "accounts because they are the same as stock_valuation account",
    )
    l10n_ro_stock_account_change = fields.Boolean(
        string="Romania - Allow stock account change from locations",
        help="Only for Romania, to change the accounts to the ones defined "
        "on stock locations",
    )

    l10n_ro_accounting_category = fields.Boolean(
        string="Romania - Is Accounting Category",
        help="Only for Romania, this define a category as accounting category",
    )
    l10n_ro_accounting_category_id = fields.Many2one(
        "product.category",
        string="Romania - Parent Accounting Category",
        help="Only for Romania, link a category on accounting category",
    )

    @api.depends("name")
    def _compute_hide_accounts(self):
        for record in self:
            record.l10n_ro_hide_stock_in_out_account = (
                self.env.company.l10n_ro_accounting
            )

    @api.constrains(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _check_valuation_accouts(self):
        """Overwrite default constraint for Romania,
        stock_valuation, stock_output and stock_input
        are the same
        """
        ro_categories = self.filtered(
            lambda x: x.l10n_ro_accounting_category
            or self.env.company.l10n_ro_accounting
        )

        for record in ro_categories:
            stock_input = record.property_stock_account_input_categ_id
            stock_output = record.property_stock_account_output_categ_id
            stock_val = record.property_stock_valuation_account_id
            if not (stock_input == stock_output == stock_val):
                raise UserError(
                    _(
                        """For Romanian Stock Accounting the stock_input,
                      stock_output and stock_valuation accounts must be
                      the same for category %s"""
                    )
                    % record.name
                )
        super(ProductCategory, self - ro_categories)._check_valuation_accouts()

    @api.onchange(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _onchange_stock_accounts(self):
        """only for Romania, stock_valuation output and input are the same"""
        if self.env.company.l10n_ro_accounting:
            for record in self:
                if record.l10n_ro_hide_stock_in_out_account:
                    # is a romanian company:
                    record.property_stock_account_input_categ_id = (
                        record.property_stock_valuation_account_id
                    )
                    record.property_stock_account_output_categ_id = (
                        record.property_stock_valuation_account_id
                    )

    def _l10n_ro_prepare_copy_values(self, values):
        for value in values:
            if value.get("l10n_ro_accounting_category_id", None):
                value.update(self._l10n_ro_prepare_copy_value(value))
        return values

    def _l10n_ro_prepare_copy_value(self, value):
        accouning_category = self.browse(value.get("l10n_ro_accounting_category_id"))
        return accouning_category._l10n_ro_copy_value(value)

    def _l10n_ro_copy_value(self, value=None):
        value = value or {}
        value.update(
            {
                "property_valuation": (
                    self.property_valuation or value.get("property_valuation")
                ),
                "property_cost_method": (
                    self.property_cost_method or value.get("property_cost_method")
                ),
                "property_stock_journal": (
                    self.property_stock_journal.id
                    or value.get("property_stock_journal")
                ),
                "property_account_income_categ_id": (
                    self.property_account_income_categ_id.id
                    or value.get("property_account_income_categ_id")
                ),
                "property_account_expense_categ_id": (
                    self.property_account_expense_categ_id.id
                    or value.get("property_account_expense_categ_id")
                ),
                "property_account_creditor_price_difference_categ": (
                    self.property_account_creditor_price_difference_categ.id
                    or value.get("property_account_creditor_price_difference_categ")
                ),
                "property_stock_account_input_categ_id": (
                    self.property_stock_account_input_categ_id.id
                    or value.get("property_stock_account_input_categ_id")
                ),
                "property_stock_account_output_categ_id": (
                    self.property_stock_account_output_categ_id.id
                    or value.get("property_stock_account_output_categ_id")
                ),
                "property_stock_valuation_account_id": (
                    self.property_stock_valuation_account_id.id
                    or value.get("property_stock_valuation_account_id")
                ),
                "l10n_ro_hide_stock_in_out_account": (
                    self.l10n_ro_hide_stock_in_out_account
                    or value.get("l10n_ro_hide_stock_in_out_account")
                ),
                "l10n_ro_stock_account_change": (
                    self.l10n_ro_stock_account_change
                    or value.get("l10n_ro_stock_account_change")
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

    def _l10n_ro_pushProductCategory_accounting(self):
        for s in self:
            value = s._l10n_ro_copy_value()
            self.search([("l10n_ro_accounting_category_id", "=", s.id)]).write(value)

    def write(self, value):
        if "l10n_ro_accounting_category" in value and not self.env.user.has_group(
            "account.group_account_manager"
        ):
            raise UserError(_("Non-Accountant User have no access on this field"))

        if value.get("l10n_ro_accounting_category_id", None):
            value = self._l10n_ro_prepare_copy_value(value)
        reset_accounting_categories = self.filtered(
            lambda x: (
                x.l10n_ro_accounting_category
                and x._l10n_ro_check_value_is_different(value)
            )
        )
        res = super(ProductCategory, self).write(value)
        if res and reset_accounting_categories:
            reset_accounting_categories._l10n_ro_pushProductCategory_accounting()
        return res

    @api.model_create_multi
    def create(self, values):
        values = self._l10n_ro_prepare_copy_values(values)
        return super(ProductCategory, self).create(values)
