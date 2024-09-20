# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import requests
import zipfile

from lxml import etree

from odoo import api, models

from odoo.addons.l10n_ro_efactura.models.ciusro_document import (
    NS_HEADER,
    make_efactura_request,
)


class L10nRoEdiDocument(models.Model):
    _inherit = "l10n_ro_edi.document"

    @api.model
    def _request_ciusro_download_zipfile(self, company, key_download, session):
        """
        This method makes a "Download Answer" (GET/descarcare) request to the Romanian SPV. It then processes the
        response by opening the received zip file and returns either:

        - {'error': <str>} ~ failing response from a bad request / unaccepted XML answer from the SPV
        - <successful response dictionary> ~ contains the necessary information to be stored from the SPV

        :param company: ``res.company`` object
        :param key_download: Content of `key_download` received from `_request_ciusro_send_invoice`
        :param session: ``requests.Session()`` object
        :return: {'error': <str>} | {'attachment_raw': <str>, 'key_signature': <str>, 'key_certificate': <str>}
        """
        if self.env.context.get("test_data"):
            return self.env.context["test_data"]
        result = make_efactura_request(
            session=requests,
            company=company,
            endpoint="descarcare",
            method="GET",
            params={"id": key_download},
        )
        if "error" in result:
            return result

        # E-Factura gives download response in ZIP format
        zip_ref = zipfile.ZipFile(io.BytesIO(result["content"]))
        xml_file = next(file for file in zip_ref.namelist() if "semnatura" not in file)
        xml_bytes = zip_ref.open(xml_file)
        root = etree.parse(xml_bytes)
        error_element = root.find(".//ns:Error", namespaces=NS_HEADER)
        if error_element is not None:
            return {"error": error_element.get("errorMessage")}

        # Pretty-print the XML content of the signature file to be saved as attachment
        attachment_raw = etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        return {
            "attachment_zip": result["content"],
            "attachment_raw": attachment_raw,
        }
