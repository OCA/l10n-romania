# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_accounting = fields.Boolean(string="Use Romanian Accounting")
    l10n_ro_share_capital = fields.Float(
        string="Ro Share Capital", digits="Account", default=200
    )
    l10n_ro_caen_code = fields.Char(
        related="partner_id.l10n_ro_caen_code", readonly=False
    )
    l10n_ro_account_serv_sale_tax_id = fields.Many2one(
        "account.tax", string="Ro Default Services Sale Tax"
    )
    l10n_ro_account_serv_purchase_tax_id = fields.Many2one(
        "account.tax", string="Ro Default Services Purchase Tax"
    )
    l10n_ro_property_vat_on_payment_position_id = fields.Many2one(
        "account.fiscal.position", "Ro Fiscal Position for VAT on Payment"
    )
    l10n_ro_property_inverse_taxation_position_id = fields.Many2one(
        "account.fiscal.position", "Ro Fiscal Position for Inverse Taxation"
    )

    l10n_ro_property_stock_picking_payable_account_id = fields.Many2one(
        "account.account",
        string="Ro Picking Account Payable",
        domain="[('internal_type', 'in', ['payable','other'])]",
        help="This account will be used as the payable account for the "
        "current partner on stock picking notice.",
    )
    l10n_ro_property_stock_picking_receivable_account_id = fields.Many2one(
        "account.account",
        string="Ro Picking Account Receivable",
        domain="[('internal_type', 'in', ['receivable','other'])]",
        help="This account will be used as the receivable account for the "
        "current partner on stock picking notice.",
    )
    l10n_ro_property_stock_usage_giving_account_id = fields.Many2one(
        "account.account",
        string="Ro Usage Giving Account",
        domain="[('internal_type', '=', 'other')]",
        help="This account will be used as the usage giving "
        "account in account move line.",
    )
    l10n_ro_property_stock_picking_custody_account_id = fields.Many2one(
        "account.account",
        string="Ro Picking Account Custody",
        help="This account will be used as the extra trial balance payable "
        "account for the current partner on stock picking received "
        "in custody.",
    )
    l10n_ro_property_uneligible_tax_account_id = fields.Many2one(
        "account.account",
        string="Ro Not Eligible Tax Account",
        domain="[('internal_type', '=', 'other')]",
        help="This account will be used as the not eligible tax account for "
        "account move line.\nUsed in especially in inventory losses.",
    )
    l10n_ro_property_stock_transfer_account_id = fields.Many2one(
        "account.account",
        string="Ro Company Stock Transfer Account",
        domain="[('internal_type', '=', 'other')]",
        help="This account will be used as an intermediary account for "
        "account move line generated from internal moves between company "
        "stores.",
    )

    l10n_ro_property_trade_discount_received_account_id = fields.Many2one(
        "account.account", string="Ro Trade discounts received"
    )
    l10n_ro_property_trade_discount_granted_account_id = fields.Many2one(
        "account.account", string="Ro Trade discounts granted"
    )

    l10n_ro_stock_acc_price_diff = fields.Boolean(
        string="Ro Stock Valuation Update",
        help="If this field is checked and the company use Romanian Accounting,"
        "the currency rate differences between reception and invoice "
        "will be reflected in the stock valuation.",
    )
    l10n_ro_property_stock_price_difference_product_id = fields.Many2one(
        "product.product",
        string="Ro Price Difference Landed Cost Product",
        domain="[('type', '=', 'service')]",
        help="This product will be used to create the landed cost"
        "for the price difference between picking and bill",
    )

    def _check_is_l10n_ro_record(self, company=False):
        if not company:
            company = self
        else:
            company = self.browse(company)
        return company.l10n_ro_accounting
