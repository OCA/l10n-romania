#
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CountryCity(models.Model):
    _inherit = "res.city"

    siruta = fields.Char()
    municipality = fields.Char("Municipality")
    zipcode = fields.Char(index=True)

    def name_get(self):
        result = []
        for record in self:
            if record.municipality and record.name not in record.municipality:
                result.append(
                    (
                        record.id, "{} ({}) ({})".format(
                            record.name, record.municipality, record.state_id.code
                        )
                    )
                )
            else:
                result.append(
                    (record.id, "{} ({})".format(record.name, record.state_id.code))
                )
        return result
