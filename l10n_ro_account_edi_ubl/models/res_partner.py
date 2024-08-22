# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ro_is_government_institution = fields.Boolean(
        "Romania - Is government institution",
        help="Check this if the partner is a government institution."
        "Will be used to calculate the sending of the invoice to "
        "the e-invoice system.",
    )
    l10n_ro_edi_ubl_no_send = fields.Boolean(
        "Romania - No send UBL",
        help="Check this if the partner should not receive UBL invoices.",
    )
