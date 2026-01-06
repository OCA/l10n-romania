# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # de eliminat acest camp si de utilizat account_fiscal_country_id.code == 'RO'
    l10n_ro_accounting = fields.Boolean(
        string="Romania - Use Romanian Accounting",
        default=True,
        compute="_compute_l10n_ro_accounting",
        store=True,
    )
    l10n_ro_share_capital = fields.Float(
        string="Romania - Share Capital", digits="Account", default=200
    )
    l10n_ro_caen_code = fields.Char(
        related="partner_id.l10n_ro_caen_code", readonly=False
    )
    l10n_ro_account_serv_sale_tax_id = fields.Many2one(
        "account.tax", string="Romania - Default Services Sale Tax"
    )
    l10n_ro_account_serv_purchase_tax_id = fields.Many2one(
        "account.tax", string="Romania - Default Services Purchase Tax"
    )
    l10n_ro_property_vat_on_payment_position_id = fields.Many2one(
        "account.fiscal.position", string="Romania - Fiscal Position for VAT on Payment"
    )
    l10n_ro_property_inverse_taxation_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Romania - Fiscal Position for Inverse Taxation",
    )

    l10n_ro_property_stock_picking_payable_account_id = fields.Many2one(
        "account.account",
        string="Romania - Picking Account Payable",
        domain="[('account_type', 'in', ['liability_current','income_other'])]",
        help="This account will be used as the payable account for the "
        "current partner on stock picking notice.",
    )
    l10n_ro_property_stock_picking_receivable_account_id = fields.Many2one(
        "account.account",
        string="Romania - Picking Account Receivable",
        domain="[('account_type', 'in', ['asset_current','income_other'])]",
        help="This account will be used as the receivable account for the "
        "current partner on stock picking notice.",
    )
    l10n_ro_property_stock_usage_giving_account_id = fields.Many2one(
        "account.account",
        string="Romania - Usage Giving Account",
        domain="[('account_type', '=', 'income_other')]",
        help="This account will be used as the usage giving "
        "account in account move line.",
    )
    l10n_ro_property_stock_picking_custody_account_id = fields.Many2one(
        "account.account",
        string="Romania - Picking Account Custody",
        help="This account will be used as the extra trial balance payable "
        "account for the current partner on stock picking received "
        "in custody.",
    )
    l10n_ro_property_uneligible_tax_account_id = fields.Many2one(
        "account.account",
        string="Romania - Not Eligible Tax Account",
        domain="[('account_type', 'in', ['liability_non_current','income_other'])]",
        help="This account will be used as the not eligible tax account for "
        "account move line.\nUsed in especially in inventory losses.",
    )
    l10n_ro_property_stock_transfer_account_id = fields.Many2one(
        "account.account",
        string="Romania - Company Stock Transfer Account",
        domain="[('account_type', '=', 'liability_current')]",
        help="This account will be used as an intermediary account for "
        "account move line generated from internal moves between company "
        "stores.",
    )

    l10n_ro_property_trade_discount_received_account_id = fields.Many2one(
        "account.account", string="Romania - Trade discounts received"
    )
    l10n_ro_property_trade_discount_granted_account_id = fields.Many2one(
        "account.account", string="Romania - Trade discounts granted"
    )

    l10n_ro_stock_acc_price_diff = fields.Boolean(
        string="Romania - Stock Valuation Update",
        help="If this field is checked and the company use Romanian Accounting,"
        "the currency rate differences between reception and invoice "
        "will be reflected in the stock valuation.",
    )
    l10n_ro_property_stock_price_difference_product_id = fields.Many2one(
        "product.product",
        string="Romania - Price Difference Landed Cost Product",
        domain="[('type', '=', 'service')]",
        help="This product will be used to create the landed cost"
        "for the price difference between picking and bill",
    )
    l10n_ro_property_customs_duty_product_id = fields.Many2one(
        "product.product",
        string="Romania - Customs Duty Landed Cost Product",
        domain="[('type', '=', 'service')]",
        help="This product will be used in create the DVI landed costfor the duty tax",
    )
    l10n_ro_property_customs_commission_product_id = fields.Many2one(
        "product.product",
        string="Romania - Customs Commission Landed Cost Product",
        domain="[('type', '=', 'service')]",
        help="This product will be used in create the DVI landed cost"
        "for the duty commissions.",
    )

    l10n_ro_stock_account_svl_lot_allocation = fields.Boolean(
        string="Romania - Stock Accounting Valuation Lot/Serial allocation",
        help="If this field is checked and the company use Romanian Accounting,"
        "the value used for stock out operations will be the value recorded at the "
        "reception of the lot/serial, ignoring FIFO rule;"
        "If this field is NOT checked and the company use Romanian Accounting,"
        "the value used for stock out operations will be the value provided "
        "by FIFO rule, applied strictly on a location level (including its children)",
    )

    l10n_ro_restrict_stock_move_date_last_month = fields.Boolean(
        string="Restrict Stock Move Date Last Month",
        help="Restrict stock move posting from 1st of previous month till today. "
        "Future dates are not allowed.",
    )
    l10n_ro_nondeductible_account_id = fields.Many2one(
        "account.account",
        string="Romania - Non Deductible Expense Account",
        help="This account will be used as the default non deductible "
        "expense account from "
        "tax repartition lines marked as not deductible."
        " If the line account does not have "
        "a non deductible account set, this account will be used.",
    )

    def _check_is_l10n_ro_record(self, company=False):
        if not company:
            company = self
        else:
            company = self.browse(company)
        return company.l10n_ro_accounting

    @api.depends("chart_template")
    def _compute_l10n_ro_accounting(self):
        for company in self:
            company.l10n_ro_accounting = company.chart_template == "ro"
