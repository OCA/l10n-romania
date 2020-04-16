# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestHrContract(common.SavepointCase):
    def test_name_get(self):
        name_var = 'https://github.com/OdooERPRomania/l10n-' \
                   'romania/blob/11.0-add-hr_payroll/l10n_ro_' \
                   'hr_payroll/tests/common.py'
        insurance_type = self.env['hr.insurance.type'].create({
            'type': '1',
            'code': '1',
            'name': name_var
        })
        result = insurance_type.name_get()[0][1]

        self.assertEqual(result, '1 - ' + name_var[:50])
