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
        string="Hide Odoo Stock In/Out Accounts",
        help="Only for Romania, to hide stock_input and stock_output "
        "accounts because they are the same as stock_valuation account",
    )
    l10n_ro_stock_account_change = fields.Boolean(
        string="Allow stock account change from locations",
        help="Only for Romania, to change the accounts to the ones defined "
        "on stock locations",
    )

    @api.depends("name")
    def _compute_hide_accounts(self):
        for record in self:
            record.l10n_ro_hide_stock_in_out_account = (
                self.env.company.l10n_ro_accounting
            )

    @api.constrains(
        lambda self: tuple(
            self._get_stock_account_property_field_names() + ["property_valuation"]
        )
    )
    def _check_valuation_accounts(self):
        """Overwrite default constraint for Romania,
        stock_valuation, stock_output and stock_input
        are the same
        """
        if self.env.company.l10n_ro_accounting:
            # is a romanian company:
            for record in self.filtered("is_l10n_ro_record"):
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
        else:
            return super()._check_valuation_accounts()

    @api.onchange(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _onchange_stock_accounts(self):
        """only for Romania, stock_valuation output and input are the same"""
        for record in self:
            if record.is_l10n_ro_record or self.env.company.l10n_ro_accounting:
                if record.l10n_ro_hide_stock_in_out_account:
                    # is a romanian company:
                    record.property_stock_account_input_categ_id = (
                        record.property_stock_valuation_account_id
                    )
                    record.property_stock_account_output_categ_id = (
                        record.property_stock_valuation_account_id
                    )
