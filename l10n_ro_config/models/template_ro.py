# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ro", "res.company")
    def _get_ro_res_company(self):
        res = super()._get_ro_res_company()
        res[self.env.company.id].update(
            {
                "account_stock_valuation_id": "pcg_371",
                "l10n_ro_account_serv_sale_tax_id": "tvac_21_s",
                "l10n_ro_account_serv_purchase_tax_id": "tvad_21_s",
                "l10n_ro_property_vat_on_payment_position_id": "fiscal_position_template_8",  # noqa
                "l10n_ro_property_inverse_taxation_position_id": "fiscal_position_template_2",  # noqa
                "l10n_ro_property_stock_picking_payable_account_id": "pcg_4081",
                "l10n_ro_property_stock_picking_receivable_account_id": "pcg_418",
                "l10n_ro_property_stock_usage_giving_account_id": "pcg_8035",
                "l10n_ro_property_stock_picking_custody_account_id": "pcg_8033",
                "l10n_ro_property_uneligible_tax_account_id": "pcg_6352",
                "l10n_ro_property_stock_transfer_account_id": "pcg_482",
            }
        )
        return res
