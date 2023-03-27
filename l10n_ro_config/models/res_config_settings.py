# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _name = "res.config.settings"
    _inherit = ["res.config.settings", "l10n.ro.mixin"]

    l10n_ro_accounting = fields.Boolean(
        related="company_id.l10n_ro_accounting",
        readonly=False,
    )
    use_anglo_saxon = fields.Boolean(
        related="company_id.anglo_saxon_accounting",
        readonly=False,
    )
    l10n_ro_caen_code = fields.Char(
        related="company_id.l10n_ro_caen_code",
        readonly=False,
    )
    l10n_ro_serv_sale_tax_id = fields.Many2one(
        "account.tax",
        related="company_id.l10n_ro_account_serv_sale_tax_id",
        readonly=False,
    )
    l10n_ro_serv_purchase_tax_id = fields.Many2one(
        "account.tax",
        related="company_id.l10n_ro_account_serv_purchase_tax_id",
        readonly=False,
    )

    l10n_ro_property_vat_on_payment_position_id = fields.Many2one(
        "account.fiscal.position",
        related="company_id.l10n_ro_property_vat_on_payment_position_id",
        readonly=False,
    )

    l10n_ro_property_inverse_taxation_position_id = fields.Many2one(
        "account.fiscal.position",
        related="company_id.l10n_ro_property_inverse_taxation_position_id",
        readonly=False,
    )

    l10n_ro_property_stock_picking_payable_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_stock_picking_payable_account_id",
        readonly=False,
    )
    l10n_ro_property_stock_picking_receivable_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_stock_picking_receivable_account_id",
        readonly=False,
    )
    l10n_ro_property_stock_usage_giving_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_stock_usage_giving_account_id",
        readonly=False,
    )
    l10n_ro_property_stock_picking_custody_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_stock_picking_custody_account_id",
        readonly=False,
    )
    l10n_ro_property_uneligible_tax_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_uneligible_tax_account_id",
        readonly=False,
    )
    l10n_ro_property_stock_transfer_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_stock_transfer_account_id",
        readonly=False,
    )

    l10n_ro_property_trade_discount_received_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_trade_discount_received_account_id",
        readonly=False,
    )
    l10n_ro_property_trade_discount_granted_account_id = fields.Many2one(
        "account.account",
        related="company_id.l10n_ro_property_trade_discount_granted_account_id",
        readonly=False,
    )

    l10n_ro_stock_acc_price_diff = fields.Boolean(
        related="company_id.l10n_ro_stock_acc_price_diff", readonly=False
    )
    l10n_ro_property_stock_price_difference_product_id = fields.Many2one(
        "product.product",
        related="company_id.l10n_ro_property_stock_price_difference_product_id",
        readonly=False,
    )
    l10n_ro_property_customs_duty_product_id = fields.Many2one(
        "product.product",
        related="company_id.l10n_ro_property_customs_duty_product_id",
        readonly=False,
    )
    l10n_ro_property_customs_commision_product_id = fields.Many2one(
        "product.product",
        related="company_id.l10n_ro_property_customs_commision_product_id",
        readonly=False,
    )
    l10n_ro_stock_account_svl_lot_allocation = fields.Boolean(
        related="company_id.l10n_ro_stock_account_svl_lot_allocation",
        readonly=False,
    )
    l10n_ro_stock_account_svl_lot_allocation_visible = fields.Boolean(default=False)

    module_currency_rate_update_RO_BNR = fields.Boolean(
        "Currency Rate Update BNR",
        help="This option allows you to manage the update of currency "
        "rate based from BNR site.",
    )
    module_l10n_ro_address_extended = fields.Boolean(
        "Romanian Extended Address",
        help="Extend the  partner addres field with flat number, staircase..",
    )
    module_l10n_ro_city = fields.Boolean(
        "Romanian Cities",
        help="This allows you to manage the Romanian Cities:\n "
        "The address fields will contain city, municipality, siruta.",
    )
    module_l10n_ro_siruta = fields.Boolean(
        "Romanian SIRUTA",
        help="This allows you to manage the Romanian Zones, Communes\n "
        "The address fields will contain new many2one to communes and zones.",
    )
    module_l10n_ro_partner_unique = fields.Boolean(
        "Partners unique by Company, VAT, NRC",
        help="This allows you to set unique partners by " "company, VAT and NRC.",
    )
    module_l10n_ro_partner_create_by_vat = fields.Boolean(
        "Create Partners by VAT",
        help="This allows you to create partners based on VAT:\n"
        "Romanian partners will be create based on ANAF webservice.\n"
        "European partners will be create based on VIES webservice "
        "(for countries that allow). \n",
    )
    module_l10n_ro_fiscal_validation = fields.Boolean(
        "Partners Fiscal Validation",
        help="This allows you to manage the vat subjected and vat on payment "
        "fields update:\n"
        "For Romanian partners based on ANAF webservice.\n"
        "For European partners based on VIES data.",
    )
    module_l10n_ro_vat_on_payment = fields.Boolean(
        "VAT on payment",
        help="This module will download data from ANAF site and when you "
        "give or receive a invoice will set fiscal position for VAT "
        "on payment",
    )
    module_l10n_ro_account_period_close = fields.Boolean(
        "Romania Account Period Close",
        help="This allows you to close accounts on periods based on "
        "templates: Income, Expense, VAT...",
    )
    module_l10n_ro_payment_receipt_report = fields.Boolean(
        "Romania Payment Receipt Report"
    )
    module_l10n_ro_nondeductible_vat = fields.Boolean("Romania Non Deductible VAT")
    module_l10n_ro_payment_to_statement = fields.Boolean("Romania Payment to Statement")
    module_l10n_ro_account_anaf_sync = fields.Boolean(
        "Account ANAF Sync",
        help="This option allows you to manage the sync to ANAF website.",
    )
    module_l10n_ro_account_report_invoice = fields.Boolean(
        "Invoice Report",
        help="This allows you to print invoice report based on " "romanian layout.\n",
    )
    module_l10n_ro_account_edit_currency_rate = fields.Boolean(
        "Invoice Edit Currency Rate",
        help="This allows you to the currency rate in invoices.\n",
    )
    module_l10n_ro_stock = fields.Boolean(
        "Romanian Stock",
        help="This module add on each warehouse methods of usage "
        "giving and consumption",
    )
    module_l10n_ro_stock_account = fields.Boolean(
        "Romanian Stock Accounting",
        help="This allows you to manage the Romanian Stock Accounting, "
        "for locations with warehouse merchandise, including:\n"
        "New stock accounts on location to allow moving entry in "
        "accounting based on the stock move.\n"
        "The account entry will be generated from stock move instead of "
        "stock quant, link with the generated account move lines on the "
        "picking\n"
        "Inventory account move lines...",
    )
    module_l10n_ro_stock_price_difference = fields.Boolean(
        "Romanian Stock Accounting Price Difference",
        help="This allows you to manage price differences between "
        "receptions and invoices.\n"
        "It will be done by using landed cost, to also threat "
        "deliveries between reception and supplier invoice confirmation.\n",
    )
    module_l10n_ro_stock_account_notice = fields.Boolean(
        "Romanian Stock Account Notice",
    )
    module_l10n_ro_stock_account_date = fields.Boolean(
        "Romanian Stock Accounting Date",
        help="This allows you to set up the Accounting Date on stock operation",
    )
    module_l10n_ro_stock_account_date_wizard = fields.Boolean(
        "Romanian Stock Accounting Date Wizard",
        help="This allows you to set up the Accounting Date on stock operation."
        "The Accounting Date will be showed up in confirmation wizards.",
    )
    module_l10n_ro_stock_report = fields.Boolean(
        "Romanian Stock Sheet Report",
    )
    module_l10n_ro_stock_picking_valued_report = fields.Boolean(
        "Romanian Stock Picking Valued Report"
    )
    module_l10n_ro_stock_picking_comment_template = fields.Boolean(
        "Romanian Stock Picking Comment Template"
    )
    module_l10n_ro_dvi = fields.Boolean("Romanian DVI")

    @api.onchange("l10n_ro_stock_account_svl_lot_allocation")
    def onchange_svl_lot_allocation(self):
        warning = ""
        if (
            self.company_id.l10n_ro_stock_account_svl_lot_allocation is False
            and self.l10n_ro_stock_account_svl_lot_allocation is True
        ):
            warning += _(
                "The values used for stock out operations will not follow FIFO rule!"
            )

            no_tracking_products = self.env["product.template"].search(
                [("tracking", "=", "none"), ("type", "!=", "service")]
            )
            if no_tracking_products.exists():
                error = _(
                    "Tracking (Lot/Serial) has to be enabled first "
                    "for all stockable and consumable products !"
                )
                raise ValidationError(error)

        if warning:
            return {"warning": {"title": _("Notification !"), "message": warning}}

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        IrModule = self.env["ir.module.module"]
        stock_mod = IrModule.search([("name", "=", "stock")])
        res["l10n_ro_stock_account_svl_lot_allocation_visible"] = (
            stock_mod.state == "installed"
        )
        return res
