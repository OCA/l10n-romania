# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def init(self):
        """This method will set romanian companies correctly"""
        ro_comp = self.sudo().search(
            [("partner_id.country_id", "=", self.env.ref("base.ro").id)]
        )
        ro_comp.write(
            {
                "l10n_ro_accounting": True,
                "anglo_saxon_accounting": True,
                "l10n_ro_stock_acc_price_diff": True,
            }
        )
