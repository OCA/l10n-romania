# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models

# the sequence of each kind of document of a romanian cash journal, and the
# suffix its code and prefix are made of
L10N_RO_CASH_SEQUENCES = {
    "l10n_ro_journal_sequence_id": "",
    "l10n_ro_statement_sequence_id": "RC",
    "l10n_ro_cash_in_sequence_id": "DI",
    "l10n_ro_cash_out_sequence_id": "DP",
    "l10n_ro_customer_cash_in_sequence_id": "CH",
}
# the names coming from those sequences are not the ones odoo builds itself
L10N_RO_SEQUENCE_REGEX = r"^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$"


class AccountJournal(models.Model):
    _name = "account.journal"
    _inherit = ["account.journal", "l10n.ro.mixin"]

    l10n_ro_statement_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Statement Sequence",
        copy=False,
        help="Sequence used for statement name",
    )
    l10n_ro_auto_statement = fields.Boolean(
        string="Romania - Auto Statement",
        help="Automatically add the payments of this cash journal to the "
        "cash register (statement) of their day",
    )
    l10n_ro_journal_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Sequence Journal",
        copy=False,
        help="Sequence used for other (closing, line) account move names",
    )
    l10n_ro_cash_in_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Sequence cash in",
        copy=False,
        help="Sequence used for cash in operations",
    )
    l10n_ro_cash_out_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Sequence cash out",
        copy=False,
        help="Sequence used for cash out operations",
    )
    l10n_ro_customer_cash_in_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Customer sequence cash in",
        copy=False,
        help="Sequence used for customer cash in operations (customer payments)",
    )
    #

    @api.model_create_multi
    def create(self, vals_list):
        journals = super().create(vals_list)
        for journal, vals in zip(journals, vals_list, strict=True):
            journal._l10n_ro_setup_cash_journal(vals)
        return journals

    def _l10n_ro_setup_cash_journal(self, vals):
        """A romanian cash journal numbers its documents with own sequences.

        Called on creation only: the code of the journal, which names the
        sequences, is settled by then.
        """
        self.ensure_one()
        if self.type != "cash" or not self.is_l10n_ro_record:
            return
        values = {
            field: self._l10n_ro_create_sequence(suffix).id
            for field, suffix in L10N_RO_CASH_SEQUENCES.items()
            if not self[field]
        }
        if not self.sequence_override_regex:
            values["sequence_override_regex"] = L10N_RO_SEQUENCE_REGEX
        if "l10n_ro_auto_statement" not in vals:
            # a romanian cash journal keeps a cash register unless told not to
            values["l10n_ro_auto_statement"] = True
        self.write(values)

    def _l10n_ro_create_sequence(self, suffix):
        """Sequence giving the numbers of one kind of cash document."""
        self.ensure_one()
        code = f"{self.code}{suffix}"
        return (
            self.env["ir.sequence"]
            .sudo()
            .create(
                {
                    "name": f"{self.name} - {code}",
                    "code": code,
                    "implementation": "no_gap",
                    "prefix": code,
                    "padding": 6,
                    "company_id": self.company_id.id,
                }
            )
        )
