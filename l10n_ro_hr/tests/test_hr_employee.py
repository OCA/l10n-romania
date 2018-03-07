# Copyright  2017 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestHREmployeebase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestHREmployeebase, cls).setUpClass()
        cls.employee_root = cls.env.ref('hr.employee_root')
        cls.employee_mit = cls.env.ref('hr.employee_mit')
        cls.employee_al = cls.env.ref('hr.employee_al')

        cls.root_ppso = cls.env.ref('l10n_ro_hr.root_ppso')
        cls.root_ppsp = cls.env.ref('l10n_ro_hr.root_ppsp')
        cls.al_also1 = cls.env.ref('l10n_ro_hr.al_also1')
        cls.al_also2 = cls.env.ref('l10n_ro_hr.al_also1')
        cls.al_alsp = cls.env.ref('l10n_ro_hr.al_also1')


class TestEmployeeRelated(TestHREmployeebase):
    def test_person_related_validation(self):
        # Test ssnid validation
        with self.assertRaises(Exception):
            self.root_ppso.ssnid = '1980511469378'
        # Test relation validation
        with self.assertRaises(Exception):
            self.root_ppso.relation = 'coinsured'

    def test_employee_related(self):
        # Test employee related calculation
        self.root_ppsp.relation_type = 'both'
        self.assertEqual(self.employee_root.person_in_care, 2)

    def test_onchange_ssnid(self):
        ''' Check onchange ssnid.'''
        # Test onchange from ANAF
        with self.env.do_in_onchange():
            self.employee_root.ssnid = '1701224378225'
            self.employee_root._ssnid_birthday_gender()
            self.assertEqual(self.employee_root.gender, 'male')
            self.assertEqual(self.employee_root.birthday, '1970-12-24')
            self.assertEqual(self.employee_root.place_of_birth, 'Vaslui')
