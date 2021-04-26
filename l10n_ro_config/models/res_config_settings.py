# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_romanian_accounting = fields.Boolean(
        string="Romanian Accounting",
        related="company_id.romanian_accounting",
        readonly=False,
    )
    serv_sale_tax_id = fields.Many2one(
        "account.tax",
        string="Default Services Sale Tax",
        related="company_id.account_serv_sale_tax_id",
        readonly=False,
    )
    serv_purchase_tax_id = fields.Many2one(
        "account.tax",
        string="Default Services Purchase Tax",
        related="company_id.account_serv_purchase_tax_id",
        readonly=False,
    )
    caen_code = fields.Char(
        string="CAEN Code",
        related="company_id.caen_code",
        readonly=False,
    )
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

    # Partners creation and Validations
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

    # Accounting Modules
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

    # Accounting Reports
    module_l10n_ro_account_report_invoice = fields.Boolean(
        "Invoice Report",
        help="This allows you to print invoice report based on " "romanian layout.\n",
    )
    module_l10n_ro_account_report_trial_balance = fields.Boolean(
        "Account Trial Balance Report",
        help="This module will add the Trial Balance report " "with multiple columns.",
    )
    module_l10n_ro_intrastat = fields.Boolean(
        "Account Intrastat Report", help="This module will add the Intrastat report."
    )

    # stock section
    use_anglo_saxon = fields.Boolean(
        string="Anglo-Saxon Accounting",
        related="company_id.anglo_saxon_accounting",
        readonly=False,
    )
    use_romanian_accounting = fields.Boolean(
        string="Use Romanian Accounting",
        related="company_id.romanian_accounting",
        readonly=False,
    )
    stock_acc_price_diff = fields.Boolean(
        related="company_id.stock_acc_price_diff", readonly=False
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
    module_l10n_ro_stock_account_store = fields.Boolean(
        "Romanian Stock Accounting - Store",
        help="This allows you to manage the Romanian Stock Accounting, "
        "for locations with store merchandise",
    )
    module_l10n_ro_stock_picking_report = fields.Boolean(
        "Stock Picking Report",
        help="This allows you to print Reports for Reception and Delivery",
    )
    module_l10n_ro_stock_picking_report_store = fields.Boolean(
        "Stock Picking Report - Store",
        help="This allows you to print Reports for Reception and Delivery",
    )
    module_l10n_ro_dvi = fields.Boolean(
        "Romanian Customs Tax Declaration",
        help="This module add possibility to register tax declaration on imports",
    )
    property_stock_picking_payable_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_picking_payable_account_id",
        readonly=False,
    )
    property_stock_picking_receivable_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_picking_receivable_account_id",
        readonly=False,
    )
    property_stock_usage_giving_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_usage_giving_account_id",
        readonly=False,
    )
    property_stock_picking_custody_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_picking_custody_account_id",
        readonly=False,
    )
    property_uneligible_tax_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_uneligible_tax_account_id",
        readonly=False,
    )
    property_stock_transfer_account_id = fields.Many2one(
        "account.account",
        related="company_id.property_stock_transfer_account_id",
        readonly=False,
    )

    property_trade_discount_received_account_id = fields.Many2one(
        "account.account",
        string="Trade discounts received",
        related="company_id.property_trade_discount_received_account_id",
        readonly=False,
    )

    property_trade_discount_granted_account_id = fields.Many2one(
        "account.account",
        string="Trade discounts granted",
        related="company_id.property_trade_discount_granted_account_id",
        readonly=False,
    )

    property_vat_on_payment_position_id = fields.Many2one(
        "account.fiscal.position",
        string="VAT on Payment",
        related="company_id.property_vat_on_payment_position_id",
        readonly=False,
    )

    property_inverse_taxation_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Inverse Taxation",
        related="company_id.property_inverse_taxation_position_id",
        readonly=False,
    )
