# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_stock_acc_price_diff = fields.Boolean(default=True)
    anglo_saxon_accounting = fields.Boolean(default=True)

    # def init(self):
    #     """This method will set romanian companies correctly"""
    #     ro_comp = self.sudo().search(
    #         [("partner_id.country_id", "=", self.env.ref("base.ro").id)]
    #     )
    #
    #     self._cr.execute(
    #         """UPDATE res_company
    #             SET
    #                 l10n_ro_accounting = TRUE,
    #                 anglo_saxon_accounting = TRUE,
    #                 l10n_ro_stock_acc_price_diff = TRUE
    #             WHERE id in %s""",
    #         (tuple(ro_comp.ids),),
    #     )
    #     return super(ResCompany, self).init()
