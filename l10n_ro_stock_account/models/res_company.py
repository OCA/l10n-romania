# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fifo_per_location = fields.Boolean(
        string="FIFO per Location",
        compute="_compute_fifo_per_location",
        store=True,
        readonly=False,
        help="Enable FIFO valuation at the source location level (instead "
        "of the company level). Outgoing moves for products with "
        "cost_method=fifo are automatically split into one stock.move "
        "per FIFO layer. Defaults to True for Romanian companies; "
        "editable per company.",
    )
    fifo_location_negative_compensation = fields.Boolean(
        string="FIFO Negative Stock Compensation",
        compute="_compute_fifo_location_negative_compensation",
        store=True,
        readonly=False,
        help="When a FIFO outgoing move happens before the corresponding "
        "incoming move (negative stock on the location), its initial "
        "value is the standard_price. On the next incoming move, the "
        "module emits a correction accounting entry to align the "
        "outgoing value with the actual incoming price. Defaults to "
        "True for Romanian companies; editable per company.",
    )

    @api.depends("country_id")
    def _compute_fifo_per_location(self):
        for company in self:
            company.fifo_per_location = (
                company.country_id and company.country_id.code == "RO"
            )

    @api.depends("country_id")
    def _compute_fifo_location_negative_compensation(self):
        for company in self:
            company.fifo_location_negative_compensation = (
                company.country_id and company.country_id.code == "RO"
            )
