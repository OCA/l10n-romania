# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2018 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    usage = fields.Selection(
        selection_add=[("usage_giving", "Usage Giving"), ("consume", "Consume")],
        ondelete={"usage_giving": "set default", "consume": "set default"},
    )
    merchandise_type = fields.Selection(
        [("store", _("Store")), ("warehouse", _("Warehouse"))],
        string="Merchandise type",
        default="warehouse",
    )
