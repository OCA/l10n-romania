# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models


class IntrastatTransaction(models.Model):
    _name = "l10n_ro_intrastat.transaction"
    _description = "Intrastat Transaction"
    _rec_name = "description"

    code = fields.Char("Code", required=True, readonly=True)
    parent_id = fields.Many2one(
        "l10n_ro_intrastat.transaction", "Parent Code", readonly=True
    )
    description = fields.Text("Description", readonly=True)

    _sql_constraints = [
        ("l10n_ro_intrastat_trcodeunique", "UNIQUE (code)", "Code must be unique."),
    ]


class IntrastatTransportMode(models.Model):
    _name = "l10n_ro_intrastat.transport_mode"
    _description = "Intrastat Transport Mode"

    code = fields.Char("Code", required=True, readonly=True)
    name = fields.Char("Description", readonly=True)

    _sql_constraints = [
        ("l10n_ro_intrastat_trmodecodeunique", "UNIQUE (code)", "Code must be unique."),
    ]
