# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class CountryCity(models.Model):
    _inherit = "res.city"

    siruta = fields.Char()
    municipality = fields.Char()
    zipcode = fields.Char(index=True)

    def name_get(self):
        result = []
        for record in self:
            if record.municipality and record.name not in record.municipality:
                result.append(
                    (
                        record.id,
                        "{} ({}) ({})".format(
                            record.name, record.municipality, record.state_id.code
                        ),
                    )
                )
            else:
                result.append(
                    (record.id, "{} ({})".format(record.name, record.state_id.code))
                )
        return result
