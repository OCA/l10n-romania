# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2019 OdooERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.multi
    def _compute_rule(self, localdict):
        self.ensure_one()
        working_days = sum(
            [localdict['worked_days'].dict[x].number_of_days
             for x in localdict['worked_days'].dict])
        working_hours = sum(
            [localdict['worked_days'].dict[x].number_of_hours
             for x in localdict['worked_days'].dict])

        localdict.update({
            'working_days_hours': (working_days, working_hours),
        })
        return super(HrSalaryRule, self)._compute_rule(localdict)
