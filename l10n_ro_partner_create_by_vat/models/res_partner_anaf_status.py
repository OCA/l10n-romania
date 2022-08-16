# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartnerAnafStatus(models.Model):
    _name = "l10n.ro.res.partner.anaf.status"
    _description = "Partner Activation ANAF History"
    _order = "date desc"

    partner_id = fields.Many2one("res.partner", ondelete="cascade")
    vat_number = fields.Char(help="VAT Number without country code.", index=True)
    date = fields.Date(
        index=True,
        help="The date for ANAF interogation.",
    )
    act = fields.Char(
        "Act autorizare",
    )
    status = fields.Char("Partner Status")
    start_date = fields.Date()
    end_date = fields.Date()
    publish_date = fields.Date()
    delete_date = fields.Date()
    active_status = fields.Boolean()

    # def create(self, vals):
    #     res = super().create(vals)
    #     for record in res:
    #         if record.vat_number:
    #             record.partner_id = self.env["res.partner"].search(
    #                 [("vat_number", "=", record.vat_number)]
    #             )
    #     return res

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.vat_number:
                record.partner_id = self.env["res.partner"].search(
                    [("l10n_ro_vat_number", "=", record.vat_number)]
                )
        return res
