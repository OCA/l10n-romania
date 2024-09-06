# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
from datetime import date
from io import BytesIO
from zipfile import ZipFile

import requests

from odoo import api, fields, models, tools

ANAF_URL = "http://static.anaf.ro/static/10/Anaf/TVA_incasare/ultim_%s.zip"


class ResPartnerAnaf(models.Model):
    _name = "l10n.ro.res.partner.anaf"
    _description = "ANAF History about VAT on Payment"
    _order = "vat, operation_date DESC, end_date, start_date"

    anaf_id = fields.Char(index=True)
    vat = fields.Char(index=True)
    start_date = fields.Date(index=True)
    end_date = fields.Date(index=True)
    publish_date = fields.Date()
    operation_date = fields.Date()
    operation_type = fields.Selection(
        [("I", "Register"), ("E", "Fix error"), ("D", "Removal")],
    )

    @api.model
    def download_anaf_data(self, file_date=None):
        """Download VAT on Payment data from ANAF if the file
        was not modified in the same date
        """
        data_dir = tools.config["data_dir"]
        istoric = os.path.join(data_dir, "istoric.txt")
        if os.path.exists(istoric):
            modify = date.fromtimestamp(os.path.getmtime(istoric))
        else:
            modify = date.fromtimestamp(0)
        if not file_date:
            file_date = date.today()
        if bool(file_date - modify):
            result = requests.get(ANAF_URL % file_date.strftime("%Y%m%d"), timeout=30)
            if result.status_code == requests.codes.ok:
                files = ZipFile(BytesIO(result.content))
                files.extractall(path=str(data_dir))

    @api.model
    def _download_anaf_data(self, file_date=None):
        self.download_anaf_data(file_date=file_date)
