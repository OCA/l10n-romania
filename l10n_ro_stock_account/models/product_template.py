# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    l10n_ro_property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        string="Stock Valuation Account",
        ondelete="restrict",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        help="In Romania accounting is only one account for valuation/input/"
        "output. If this value is set, we will use it, otherwise will "
        "use the category value. ",
    )

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        company = self.company_id or self.env.company
        if not company.l10n_ro_accounting:
            return accounts

        stock_move = self.env.context.get("l10n_ro_stock_move")
        if not stock_move or not stock_move.is_l10n_ro_record:
            return accounts
        src_location = stock_move.location_id
        dest_location = stock_move.location_dest_id
        if self.categ_id.l10n_ro_stock_account_change:
            if src_location.usage == "internal":
                inc_acc = src_location.l10n_ro_property_account_income_location_id
                exp_acc = src_location.l10n_ro_property_account_expense_location_id
                stock_acc = src_location.l10n_ro_property_stock_valuation_account_id
            else:
                inc_acc = dest_location.l10n_ro_property_account_income_location_id
                exp_acc = dest_location.l10n_ro_property_account_expense_location_id
                stock_acc = dest_location.l10n_ro_property_stock_valuation_account_id

            if stock_move.l10n_ro_move_type == "internal_transfer":
                if dest_location.l10n_ro_property_stock_valuation_account_id:
                    accounts["expense"] = (
                        dest_location.l10n_ro_property_stock_valuation_account_id
                    )
                else:
                    accounts["expense"] = accounts["stock_valuation"]

            if inc_acc:
                accounts["income"] = inc_acc
            if exp_acc:
                accounts["expense"] = exp_acc
            if stock_acc:
                accounts["stock_valuation"] = stock_acc
        if company.l10n_ro_property_stock_picking_payable_account_id:
            accounts["l10n_ro_picking_payable"] = (
                company.l10n_ro_property_stock_picking_payable_account_id
            )
        if company.l10n_ro_property_stock_picking_receivable_account_id:
            accounts["l10n_ro_picking_receivable"] = (
                company.l10n_ro_property_stock_picking_receivable_account_id
            )
        if company.l10n_ro_property_stock_usage_giving_account_id:
            accounts["l10n_ro_usage_giving"] = (
                company.l10n_ro_property_stock_usage_giving_account_id
            )
        if company.l10n_ro_property_stock_transfer_account_id:
            accounts["l10n_ro_transfer"] = (
                company.l10n_ro_property_stock_transfer_account_id
            )
        if stock_move.l10n_ro_move_type in [
            "consumption",
            "consumption_return",
            "usage_giving",
            "usage_giving_return",
        ]:
            if accounts["expense"].l10n_ro_stock_consume_account_id:
                accounts["expense"] = accounts[
                    "expense"
                ].l10n_ro_stock_consume_account_id
        if accounts["stock_valuation"].l10n_ro_reception_in_progress_account_id:
            accounts["l10n_ro_reception_in_progress"] = accounts[
                "stock_valuation"
            ].l10n_ro_reception_in_progress_account_id

        warehouse = src_location.warehouse_id or dest_location.warehouse_id
        if warehouse and warehouse.l10n_ro_fiscal_position_id:
            for key in accounts.keys() - {"stock_journal"}:
                if accounts.get(key):
                    accounts[key] = warehouse.l10n_ro_fiscal_position_id.map_account(
                        accounts[key]
                    )
        return accounts
