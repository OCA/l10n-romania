# Copyright 2025 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _is_incoming(self):
        self.ensure_one()
        return (
            self.location_id.usage in ("usage_giving", "consume")
            or super()._is_incoming()
        )

    def _is_outgoing(self):
        self.ensure_one()
        return (
            self.location_dest_id.usage in ("usage_giving", "consume")
            or super()._is_outgoing()
        )
