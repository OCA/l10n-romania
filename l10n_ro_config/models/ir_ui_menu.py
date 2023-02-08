# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class L10nRoIrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    is_l10n_ro_record = fields.Boolean()
