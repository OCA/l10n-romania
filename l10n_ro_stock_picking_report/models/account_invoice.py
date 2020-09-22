# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import _, api, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def _prepare_invoice_line_from_po_line(self, line):
        data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        if self.purchase_id.partner_ref:
            if self.reference:
                if self.purchase_id.partner_ref not in self.reference:
                    self.reference += self.purchase_id.partner_ref
            else:
                self.reference = self.purchase_id.partner_ref

        return data
