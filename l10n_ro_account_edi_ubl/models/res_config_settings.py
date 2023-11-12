# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_edi_manual = fields.Boolean(
        related="company_id.l10n_ro_edi_manual",
        readonly=False,
        help="If checked, the invoice will be submitted manually to the ANAF eInvoice.",
        string="E-Invoice Manual submission",
    )

    l10n_ro_edi_residence = fields.Integer(
        related="company_id.l10n_ro_edi_residence",
        readonly=False,
        string="Residence",
    )
