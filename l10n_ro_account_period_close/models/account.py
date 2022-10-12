# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Account(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "l10n.ro.mixin"]

    l10n_ro_close_check = fields.Boolean(
        string="Romania - Bypass Closing Side Check",
        help="By checking this when you close a period, it will not respect "
        "the side of closing, meaning: expenses closed on credit side, "
        "incomed closed on debit side. \n You should check the 711xxx "
        "accounts.",
    )


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    l10n_ro_close_id = fields.Many2one(
        "l10n.ro.account.period.closing", string="Romania - Closed Account Period"
    )
    l10n_ro_closing_move = fields.Boolean(string="Romania - Is Closing Move")
