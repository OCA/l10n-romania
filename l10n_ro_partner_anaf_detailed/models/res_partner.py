# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import api, fields, models


from odoo.addons.l10n_ro_partner_create_by_vat.models import res_partner

res_partner.AnafFiled_OdooField_Overwrite.extend([
    ("anaf_data", "data", "over_all_the_time"),
    ("act", "act", "over_all_the_time"),
    ("stare_inregistrare", "stare_inregistrare", "over_all_the_time"),
    ("dataInactivare", "dataInactivare", "over_all_the_time"),
    ("dataReactivare", "dataReactivare", "over_all_the_time"),
    ("dataPublicare", "dataPublicare", "over_all_the_time"),
    ("dataRadiere", "dataRadiere", "over_all_the_time"),
    ("statusInactivi", "statusInactivi", "over_all_the_time"),

    ("scpTVA", "scpTVA", "over_all_the_time"),
    ("data_inceput_ScpTVA", "data_inceput_ScpTVA", "over_all_the_time"),
    ("data_sfarsit_ScpTVA", "data_sfarsit_ScpTVA", "over_all_the_time"),
    ("data_anul_imp_ScpTVA", "data_anul_imp_ScpTVA", "over_all_the_time"),
    ("mesaj_ScpTVA", "mesaj_ScpTVA", "over_all_the_time"),

    # are in module l10n_vat_on_payment
    # ("dataInceputTvaInc", "dataInceputTvaInc", "over_all_the_time"),
    # ("dataSfarsitTvaInc", "dataSfarsitTvaInc", "over_all_the_time"),
    # ("dataActualizareTvaInc", "dataActualizareTvaInc", "over_all_the_time"),
    # ("dataPublicareTvaInc", "dataPublicareTvaInc", "over_all_the_time"),
    # ("tipActTvaInc", "tipActTvaInc", "over_all_the_time"),
    # ("statusTvaIncasare", "statusTvaIncasare", "over_all_the_time"),


    # not used anymore
    # ("dataInceputSplitTVA", "dataInceputSplitTVA", "over_all_the_time"),
    # ("dataAnulareSplitTVA", "dataAnulareSplitTVA", "over_all_the_time"),
    # ("statusSplitTVA", "statusSplitTVA", "over_all_the_time"),
    ("iban", "iban", "over_all_the_time"),
    ("statusRO_e_Factura", "statusRO_e_Factura", "over_all_the_time"),
    ])

_logger = logging.getLogger(__name__)



class ResPartner(models.Model):
    _inherit = "res.partner"

    def _compute_anaf_status(self):
        for partner in self:
            if partner.vat_number and partner.company_id.name == "Romania":
                status = self.env["res.partner.anaf.status"].search(
                    [("cui", "=", partner.vat_number)]
                )
                partner.anaf_status_ids = [(6, 0, [line.id for line in history])]
                if self._context.get("anaf_date"):
                    last_status = status.filtered(lambda r: r.operation_date <=self._context.get("anaf_date"))
                else:
                    last_status = status[-1]
                partner.anaf_status_inactive = last_status.statusInactivi if last_status else True 
            else:
                partner.anaf_status_ids = [(6, 0, [])]
                partner.anaf_status_inactive = False

    anaf_status_inactive = fields.Boolean(
        compute="_compute_anaf_status",
        string="Company Is Inactive",
        readonly=True,
    )

    anaf_status_ids = fields.One2many(
        "res.partner.anaf.status",
        compute="_compute_anaf_status",
        string="Anaf Company Status Records",
        readonly=True,
    )

    country_name = fields.Char(related="country_id.name") # just for a xml domain

    anaf_data = fields.Date(help="The date when following anaf data is taken",)
    act = fields.Char("Act autorizare",)
    stare_inregistrare = fields.Char("Stare Societate",)
    scpTVA = fields.Boolean( help="true -pentru platitor in scopuri de tva / false in cazul in care nu"
        "e platitor  in scopuri de TVA la data cautata""",)
    data_inceput_ScpTVA = fields.Date(help="Data înregistrării în scopuri de TVA anterioară",)
    data_sfarsit_ScpTVA = fields.Date(help="Data anulării înregistrării în scopuri de TVA",)
    data_anul_imp_ScpTVA = fields.Date(help="Data operarii anularii înregistrării în scopuri de TVA",)
    mesaj_ScpTVA = fields.Char(help="MESAJ:(ne)platitor de TVA la data cautata",)

    # are in module l10n_ro_vat_on_payment
    # dataInceputTvaInc = fields.Date( help= "Data de la care aplică sistemul TVA la încasare",)
    # dataSfarsitTvaInc = fields.Date(help="Data până la care aplică sistemul TVA la încasare",)
    # dataActualizareTvaInc = fields.Date(help="Data actualizarii tva incasare",)
    # dataPublicareTvaInc = fields.Date(help="Data publicarii tva incasare",)
    # tipActTvaInc = fields.Char(help="Tip actualizare  tva incasare  'Radiere'",)
    # statusTvaIncasare = fields.Char(help="true -pentru platitor TVA la incasare/ false in"
            # " cazul in care nu e platitor de TVA la incasare la data cautata",)

    dataInactivare = fields.Date()
    dataReactivare = fields.Date()
    dataPublicare = fields.Date()
    dataRadiere = fields.Date()
    statusInactivi =fields.Boolean(help=" true -pentru inactiv / false"
        " in cazul in care nu este inactiv la data cautata")
    iban = fields.Char(help="contul IBAN taken from anaf")
    statusRO_e_Factura = fields.Boolean(help= "true - figureaza in"
        " Registrul RO e-Factura / false - nu figureaza in Registrul RO e-Factura "
        "la data cautata")
    
    def refresh_anaf_data(self):
        self.ro_vat_change()

    def _Anaf_to_Odoo(self, result):
        res = super(ResPartner, self)._Anaf_to_Odoo(result)
        if res:
            anaf_status_obj = self.env["res.partner.anaf.status"]
            anaf_request_date = result["data"]
            same_date_record = self.anaf_status_ids.filtered(lambda r: r.anaf_data==anaf_request_date)
            before_record = self.anaf_status_ids.filtered(lambda r: r.anaf_data<anaf_request_date)
            after_record = self.anaf_status_ids.filtered(lambda r: r.anaf_data>anaf_request_date)
            statusInactivi = result.get("statusInactivi")
            if  not same_date_record and (
                (before_record and after_record and before_record.statusInactivi != result.get("statusInactivi") and after_record.statusInactivi != result.get("statusInactivi")) or 
                (after_record and  after_record.statusInactivi != statusInactivi) or 
                (before_record and  before_record.statusInactivi != statusInactivi) or 
                (not self.anaf_status_ids)
                ):
                anaf_status_obj.create({
                    "cui":result["cui"],
                    "data":result["data"],
                    "act":result.get("act",""),
                    "stare_inregistrare":result.get("stare_inregistrare",""),
                    # we try to see if if something like a date - is pobable if it has a digit in it
                    "dataInactivare":result["dataInactivare"] if any([c.isdigit() for c in result.get("dataInactivare","")]) else False,
                    "dataReactivare":result["dataReactivare"] if any([c.isdigit() for c in result.get("dataReactivare","")]) else False,
                    "dataPublicare":result["dataPublicare"] if any([c.isdigit() for c in result.get("dataPublicare","")]) else False,
                    "dataRadiere":result["dataRadiere"] if any([c.isdigit() for c in result.get("dataRadiere","")]) else False,
                    "statusInactivi":statusInactivi,
                    })
            return res

 