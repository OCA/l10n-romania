# Copyright (C) 2015 Deltatech
# Copyright (C) 2015 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ["pos.order", "l10n.ro.mixin"]

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.is_l10n_ro_record and self.pos_reference:
            vals["ref"] = self.pos_reference
        return vals
