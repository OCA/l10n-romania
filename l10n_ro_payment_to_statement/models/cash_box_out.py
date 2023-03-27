# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class CashBoxOut(models.TransientModel):
    _name = "cash.box.out"
    _inherit = ["cash.box.out", "l10n.ro.mixin"]

    @api.depends("name", "amount")
    def _compute_company_partner_ids(self):
        for box in self:
            box.company_partner_ids = self.env.company.partner_id.child_ids

    l10n_ro_partner_id = fields.Many2one(
        "res.partner",
        domain="[('id', 'in', company_partner_ids)]",
        string="Romania - Partner",
        help="The partner defined in payment disposal must be set as an employee.",
    )
    company_partner_ids = fields.Many2many(
        "res.partner", compute="_compute_company_partner_ids"
    )

    @api.depends(lambda self: self._check_company_id_in_fields())
    @api.depends_context("company")
    def _compute_is_l10n_ro_record(self):
        context = dict(self._context or {})
        active_model = context.get("active_model", False)
        active_ids = context.get("active_ids", [])
        records = self.env[active_model].browse(active_ids)
        for box in self:
            if records:
                obj = records[0]
                has_company = obj._check_company_id_in_fields()
                has_company = has_company and obj.company_id
                company = obj.company_id if has_company else obj.env.company
                box.is_l10n_ro_record = company._check_is_l10n_ro_record()

    def _check_company_id_in_fields(self):
        return ["name"]

    def _calculate_values_for_statement_line(self, record):
        values = super(CashBoxOut, self)._calculate_values_for_statement_line(
            record=record
        )
        if record.is_l10n_ro_record:
            values["partner_id"] = self.l10n_ro_partner_id.id
            values["is_l10n_ro_payment_disposal"] = True
            if values["amount"] > 0:
                if record.journal_id.l10n_ro_cash_in_sequence_id:
                    values[
                        "name"
                    ] = record.journal_id.l10n_ro_cash_in_sequence_id.next_by_id()
            else:
                if record.journal_id.l10n_ro_cash_out_sequence_id:
                    values[
                        "name"
                    ] = record.journal_id.l10n_ro_cash_out_sequence_id.next_by_id()
        return values
