# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    from stdnum.ro.cnp import get_birth_date, is_valid as validate_cnp
except ImportError:
    _logger.debug("Cannot import check_vies method from python stdnum.")

# Source: http://ro.wikipedia.org/wiki/Cod_numeric_personal#JJ
birthplace = {
    "01": "Alba",
    "02": "Arad",
    "03": "Argeș",
    "04": "Bacă",
    "05": "Bihor",
    "06": "Bistrița-Năsăud",
    "07": "Botoșani",
    "08": "Brașov",
    "09": "Brăila",
    "10": "Buză",
    "11": "Caraș-Severin",
    "12": "Cluj",
    "13": "Constanța",
    "14": "Covasna",
    "15": "Dâmbovița",
    "16": "Dolj",
    "17": "Galați",
    "18": "Gorj",
    "19": "Harghita",
    "20": "Hunedoara",
    "21": "Ialomița",
    "22": "Iași",
    "23": "Ilfov",
    "24": "Maramureș",
    "25": "Mehedinți",
    "26": "Mureș",
    "27": "Neamț",
    "28": "Olt",
    "29": "Prahova",
    "30": "Satu Mare",
    "31": "Sălaj",
    "32": "Sibi",
    "33": "Suceava",
    "34": "Teleorman",
    "35": "Timiș",
    "36": "Tulcea",
    "37": "Vaslui",
    "38": "Vâlcea",
    "39": "Vrancea",
    "40": "București",
    "41": "București S.1",
    "42": "București S.2",
    "43": "București S.3",
    "44": "București S.4",
    "45": "București S.5",
    "46": "București S.6",
    "51": "Călărași",
    "52": "Giurgi",
}


class HREmployeeRelated(models.Model):
    _name = "hr.employee.related"
    _description = "Employee person in care or are coinsured"

    @api.constrains("ssnid")
    def _validate_ssnid(self):
        for relation in self:
            if relation.ssnid and not validate_cnp(relation.ssnid):
                raise ValidationError(_("Invalid SSN number"))

    @api.constrains("relation", "relation_type")
    def _validate_relation(self):
        for relation in self:
            if relation.relation_type and relation.relation:
                if (
                    relation.relation_type
                    in [
                        "coinsured",
                        "both",
                    ]
                    and relation.relation not in ("husband", "wife", "parent")
                ):
                    raise ValidationError(_("Just parents and husband/wife"))

    employee_id = fields.Many2one("hr.employee", "Employee", required=True)
    partner_id = fields.Many2one("res.partner", "Partner", required=True)
    name = fields.Char("Name", related="partner_id.name", help="Related person name")
    firstname = fields.Char(
        "First Name", related="partner_id.firstname", help="Related person first name"
    )
    lastname = fields.Char(
        "Last Name", related="partner_id.lastname", help="Related person last name"
    )
    ssnid = fields.Char("SSN No", required=True, help="Social Security Number")
    relation = fields.Selection(
        [
            ("husband", _("Husband")),
            ("wife", _("Wife")),
            ("parent", _("Parent")),
            ("child", _("Child")),
            ("firstdegree", _("First degree relationship")),
            ("secdegree", _("Second degree relationship")),
        ],
        string="Relation",
        required=True,
        default="husband",
    )
    relation_type = fields.Selection(
        [("in_care", _("In Care")), ("coinsured", _("Coinsured")), ("both", _("Both"))],
        string="Relation type",
        required=True,
        index=True,
        default="in_care",
    )


class Employee(models.Model):
    _inherit = "hr.employee"

    @api.depends("person_related")
    def _compute_person_in_care(self):
        for employee in self:
            employee.person_in_care = employee.person_related.search_count(
                [
                    ("relation_type", "in", ["in_care", "both"]),
                    ("employee_id", "=", employee.id),
                ]
            )

    @api.onchange("ssnid")
    def _ssnid_birthday_gender(self):
        gender = bplace = bday = False
        if self.ssnid and self.country_id and "RO" in self.country_id.code.upper():
            if not validate_cnp(self.ssnid):
                raise ValidationError(_("Invalid SSN number"))
            if self.ssnid[7:9] in birthplace.keys():
                bplace = birthplace[self.ssnid[7:9]]
            bday = get_birth_date(self.ssnid)
            if self.ssnid[0] in "1357":
                gender = "male"
            elif self.ssnid[0] in "2468":
                gender = "female"
        self.gender = gender
        self.birthday = bday
        self.place_of_birth = bplace

    @api.model
    def _get_casang_dict(self):
        casang_sel = [
            ("AB", "Alba"),
            ("AR", "Arad"),
            ("AG", "Arges"),
            ("BC", "Baca"),
            ("BH", "Bihor"),
            ("BN", "Bistrita-Nasaud"),
            ("CS", "Caras-Severin"),
            ("BT", "Botosani"),
            ("BR", "Braila"),
            ("BV", "Brasov"),
            ("BZ", "Buza"),
            ("CL", "Calarasi"),
            ("CJ", "Cluj"),
            ("CT", "Constanta"),
            ("CV", "Covasna"),
            ("DB", "Dambovita"),
            ("DJ", "Dolj"),
            ("GL", "Galati"),
            ("GR", "Giurgi"),
            ("GJ", "Gorj"),
            ("HR", "Harghita"),
            ("HD", "Hunedoara"),
            ("IL", "Ialomita"),
            ("IS", "Iasi"),
            ("IF", "Ilfov"),
            ("MM", "Maramures"),
            ("MH", "Mehedinti"),
            ("MS", "Mures"),
            ("NT", "Neamt"),
            ("OT", "Olt"),
            ("PH", "Prahova"),
            ("SJ", "Salaj"),
            ("SM", "Satu Mare"),
            ("SB", "Sibi"),
            ("SV", "Suceava"),
            ("TR", "Teleorman"),
            ("TM", "Timis"),
            ("TL", "Tulcea"),
            ("VS", "Vaslui"),
            ("VL", "Valcea"),
            ("VN", "Vrancea"),
            ("_B", "CAS Municipiu Bucuresti"),
            ("_A", "AOPSNAJ"),
            ("_N", "Neasigurat (zilier)"),
        ]
        return casang_sel

    ssnid_init = fields.Char("Initial SSN No", help="Initial Social Security Number")
    first_name_init = fields.Char("Initial Name")
    last_name_init = fields.Char("Initial First Name")
    casang = fields.Selection("_get_casang_dict", string="Insurance", default="AB")
    person_related = fields.One2many(
        "hr.employee.related", "employee_id", "Related Persons"
    )
    person_in_care = fields.Integer(
        string="No of persons in care",
        compute="_compute_person_in_care",
        help="Number of persons in care",
    )
    emit_by = fields.Char("Emmited by")
    emit_on = fields.Date("Emmited on")
    expires_on = fields.Date("Expires on")
