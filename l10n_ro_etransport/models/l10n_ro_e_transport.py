# Copyright (C) 2024 Deltatech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ETransportAim(models.Model):
    _name = "l10n.ro.e.transport.aim"
    _description = "E Transport Aim"

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
