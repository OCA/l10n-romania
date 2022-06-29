# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    ####################################################
    # Export
    ####################################################

    def _get_cirus_ro_values(self, invoice):
        values = super()._get_bis3_values(invoice)
        values.update(
            {
                "customization_id": "urn:cen.eu:en16931:2017"
                "#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.0",
            }
        )

        return values

    def _export_cirus_ro(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        xml_content += self.env.ref("l10n_ro_edi_ubl.export_cirus_ro_invoice")._render(
            self._get_cirus_ro_values(invoice)
        )
        xml_name = "%s.xml" % invoice._get_cirus_ro_name()
        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_content,
                "mimetype": "application/xml",
                "res_model": "account.move",
                "res_id": invoice.id,
            }
        )

    #
    # ####################################################
    # # Account.edi.format override
    # ####################################################
    #
    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        self.ensure_one()
        if (
            self.code == "cirus_ro"
            and self._is_ubl(filename, tree)
            and not self._is_account_edi_ubl_cii_available()
        ):
            return self._create_invoice_from_ubl(tree)
        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if (
            self.code == "cirus_ro"
            and self._is_ubl(filename, tree)
            and not self._is_account_edi_ubl_cii_available()
        ):
            return self._update_invoice_from_ubl(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    #
    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != "cirus_ro" or self._is_account_edi_ubl_cii_available():
            return super()._is_compatible_with_journal(journal)
        return journal.type == "sale" and journal.country_code == "RO"

    #
    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != "cirus_ro" or self._is_account_edi_ubl_cii_available():
            return super()._post_invoice_edi(invoices, test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._export_cirus_ro(invoice)
            res[invoice] = {"success": True, "attachment": attachment}
        return res
