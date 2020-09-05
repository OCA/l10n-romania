# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"

    hide_stock_in_out_account = fields.Boolean(
        compute="_compute_hide_accounts",
        help="Only for Romania, to hide stock_input and stock_output "
        "accounts because they are the same as stock_valuation account",
    )
    stock_account_change = fields.Boolean(
        string="Allow stock account change from locations",
        help="Only for Romania, to change the accounts to the ones defined "
        "on stock locations",
    )

    @api.depends("name")
    def _compute_hide_accounts(self):
        for record in self:
            if record.env.company.romanian_accounting:
                record.hide_stock_in_out_account = True
            else:
                record.hide_stock_in_out_account = False

    @api.constrains(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _check_valuation_accouts(self):
        """ Overwrite default constraint for Romania,
        stock_valuation, stock_output and stock_input
        are the same
        """
        if self.env.company.romanian_accounting:
            # is a romanian company:
            for record in self:
                stock_input = record.property_stock_account_input_categ_id
                stock_output = record.property_stock_account_output_categ_id
                stock_val = record.property_stock_valuation_account_id
                if not (stock_input == stock_output == stock_val):
                    raise UserError(
                        _(
                            "For Romanian Stock Accounting the stock_input, "
                            "stock_output and stock_valuation accounts must "
                            "bethe same for category %s" % record.name
                        )
                    )
        else:
            self.super(ProductCategory, self)._check_valuation_accouts()

    @api.onchange(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _onchange_stock_accouts(self):
        """ only for Romania, stock_valuation output and input are the same
        """
        for record in self:
            if record.hide_stock_in_out_account:
                # is a romanian company:
                record.property_stock_account_input_categ_id = (
                    record.property_stock_valuation_account_id
                )
                record.property_stock_account_output_categ_id = (
                    record.property_stock_valuation_account_id
                )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        "Stock Valuation Account",
        company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]),"
        "('deprecated', '=', False)]",
        check_company=True,
        help="In Romania accounting is only one account for valuation/input/"
        "output. If this value is set, we will use it, otherwise will "
        "use the category value. ",
    )

    def _get_product_accounts(self):

        accounts = super(ProductTemplate, self)._get_product_accounts()

        company = self.env.user.company_id
        if not company.romanian_accounting:
            return accounts
        property_stock_valuation_account_id = (
            self.property_stock_valuation_account_id
            or self.categ_id.property_stock_valuation_account_id
        )
        stock_picking_payable_account_id = (
            company.property_stock_picking_payable_account_id
        )
        stock_picking_receivable_account_id = (
            company.property_stock_picking_receivable_account_id
        )
        property_stock_usage_giving_account_id = (
            company.property_stock_usage_giving_account_id
        )

        if property_stock_valuation_account_id:
            accounts.update(
                {
                    "stock_input": property_stock_valuation_account_id,
                    "stock_output": property_stock_valuation_account_id,
                    "stock_valuation": property_stock_valuation_account_id,
                }
            )

        valued_type = self.env.context.get("valued_type", "indefinite")
        _logger.info(valued_type)
        # in nir si factura furnizor se va utiliza 408
        if valued_type in [
            "reception_notice",
            "reception_notice_return",
            "invoice_in_notice",
        ]:
            if stock_picking_payable_account_id:
                accounts["stock_input"] = stock_picking_payable_account_id

        # in aviz si factura client se va utiliza 418
        elif valued_type == "invoice_out_notice":
            if stock_picking_receivable_account_id:
                accounts["stock_output"] = stock_picking_receivable_account_id
                accounts["stock_valuation"] = accounts["income"]
                accounts["income"] = stock_picking_receivable_account_id

        # la vanzare se scoate stocul pe cheltuiala
        elif valued_type in [
            "production",
            "delivery",
            "delivery_notice",
            "production_return",
            "delivery_return",
            "delivery_notice_return",
            "minus_inventory",
            "plus_inventory",
        ]:
            accounts["stock_output"] = accounts["expense"]
            accounts["stock_input"] = accounts["expense"]

        elif valued_type == "usage_giving":
            accounts["stock_output"] = property_stock_usage_giving_account_id
            accounts["stock_input"] = property_stock_usage_giving_account_id
            accounts["stock_valuation"] = property_stock_usage_giving_account_id
        return accounts
