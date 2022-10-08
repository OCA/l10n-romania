# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class CountryCity(models.Model):
    _name = "res.city"
    _inherit = ["res.city", "l10n.ro.mixin"]

    l10n_ro_siruta = fields.Char(string="Romania - Siruta")
    l10n_ro_municipality = fields.Char(string="Romania - Municipality")
    zipcode = fields.Char(index=True)

    def name_get(self):
        result = []
        for record in self:
            if not record.is_l10n_ro_record:
                result += super(CountryCity, record).name_get()
            else:
                if (
                    record.l10n_ro_municipality
                    and record.name not in record.l10n_ro_municipality
                ):
                    result.append(
                        (
                            record.id,
                            "{} ({}) ({})".format(
                                record.name,
                                record.l10n_ro_municipality,
                                record.state_id.code,
                            ),
                        )
                    )
                else:
                    result.append(
                        (record.id, "{} ({})".format(record.name, record.state_id.code))
                    )
        return result
