# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _is_dropshipped(self):
        self.ensure_one()
        return (
            self.location_id.usage == "supplier"
            and self.location_dest_id.usage == "customer"
        )

    def _is_dropshipped_returned(self):
        self.ensure_one()
        return (
            self.location_id.usage == "customer"
            and self.location_dest_id.usage == "supplier"
        )
