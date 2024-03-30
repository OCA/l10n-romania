# Copyright (C) 2024 Deltatech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ETransportScope(models.Model):
    _name = "l10n.ro.e.transport.scope"
    _description = "E Transport Scope"

    name = fields.Char(required=True)
    code = fields.Char(required=True)


class ETransportCustoms(models.Model):
    _name = "l10n.ro.e.transport.customs"
    _description = "E Transport Customs"

    name = fields.Char(required=True)
    code = fields.Char(required=True)


class ETransportOperation(models.Model):
    _name = "l10n.ro.e.transport.operation"
    _description = "E Transport Operation"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    usage = fields.Selection(
        [("import", "Import"), ("export", "Export"), ("local", "Local")], required=True
    )
