# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    # Prin acest camp se indica daca un produs care e stocabil trece prin
    # contul 408 / 418 la achizitie sau vanzare
    # receptie/ livrare in baza de aviz
    l10n_ro_notice = fields.Boolean(
        string="Romania - Is a notice",
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        default=False,
        help="With this field the reception/delivery is set as a notice. "
        "The generated account move will contain accounts 408/418.",
    )
