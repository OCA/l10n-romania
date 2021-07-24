# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details


from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    statement_id = fields.Many2one(
        "account.bank.statement",
        string="Statement",
        domain="[('journal_id','=',journal_id)]",
    )

    statement_line_id = fields.Many2one(
        "account.bank.statement.line",
        string="Statement Line",
        readonly=True,
        domain="[('statement_id','=',statement_id)]",
    )

    @api.onchange("date", "journal_id")
    def onchange_date_journal(self):
        domain = [("date", "=", self.date), ("journal_id", "=", self.journal_id.id)]
        statement = self.env["account.bank.statement"].search(domain, limit=1)
        if statement:
            self.statement_id = statement
        else:
            # daca tipul este numerar trebuie generat
            if self.journal_id.auto_statement:
                values = {
                    "journal_id": self.journal_id.id,
                    "date": self.date,
                    "name": "/",
                }
                self.statement_id = (
                    self.env["account.bank.statement"].sudo().create(values)
                )

    def action_post(self):
        not_posted_before = self.env["account.payment"]
        for rec in self:
            if not rec.posted_before:
                not_posted_before |= rec
        res = super(AccountPayment, self).action_post()
        # here the payments have name form account.move sequence_mixin
        # if type is customer and type cash we are going to give them name from choosen sequences
        for rec in not_posted_before:
            if rec.partner_type == "customer" and rec.journal_id.type == "cash":
                if rec.journal_id.cash_in_sequence_id and rec.payment_type == "inbound":
                    rec.name = rec.journal_id.cash_in_sequence_id.next_by_id()
        #                if rec.journal_id.cash_out_sequence_id and rec.payment_type == "outbound":
        #                    rec.name = rec.journal_id.cash_out_sequence_id.next_by_id()
        self.add_statement_line()

        return res

    def get_reconciled_statement_line(self):
        for payment in self:
            for move_line in payment.reconciled_statement_ids:
                if move_line.statement_id and move_line.statement_line_id:
                    payment.write(
                        {
                            "statement_id": move_line.statement_id.id,
                            "statement_line_id": move_line.statement_line_id.id,
                        }
                    )

    def add_statement_line(self):
        lines = self.env["account.bank.statement.line"]
        self.get_reconciled_statement_line()
        for payment in self:
            auto_statement = payment.journal_id.auto_statement
            if (
                auto_statement
                and not payment.statement_id
                and not payment.reconciled_statement_ids
            ):
                domain = [
                    ("date", "=", payment.date),
                    ("journal_id", "=", payment.journal_id.id),
                ]
                statement = self.env["account.bank.statement"].search(domain, limit=1)
                if not statement:
                    values = {
                        "journal_id": payment.journal_id.id,
                        "date": payment.date,
                        "name": "/",
                    }
                    statement = payment.env["account.bank.statement"].create(values)
                payment.write({"statement_id": statement.id})

            if (
                payment.state == "posted"
                and not payment.statement_line_id
                and payment.statement_id
            ):
                ref = ""
                for invoice in payment.reconciled_bill_ids:
                    ref += invoice.name
                for invoice in payment.reconciled_invoice_ids:
                    ref += invoice.name
                values = {
                    # "name": payment.communication or payment.name,
                    "statement_id": payment.statement_id.id,
                    "date": payment.date,
                    "partner_id": payment.partner_id.id,
                    "amount": payment.amount,
                    "payment_id": payment.id,
                    "ref": ref,
                    "payment_ref": payment.name,
                }
                if payment.payment_type == "outbound":
                    values["amount"] = -1 * payment.amount

                line = payment.env["account.bank.statement.line"].create(values)
                lines |= line
                payment.write({"statement_line_id": line.id})

    def unlink(self):
        statement_line_ids = self.env["account.bank.statement.line"]
        for payment in self:
            statement_line_ids |= payment.statement_line_id
        res = super().unlink()
        statement_line_ids.unlink()
        return res


class PosBoxOut(models.TransientModel):
    _inherit = "cash.box.out"

    def _calculate_values_for_statement_line(self, record):
        values = super(PosBoxOut, self)._calculate_values_for_statement_line(
            record=record
        )
        if values["amount"] > 0:
            if record.journal_id.cash_in_sequence_id:
                values["name"] = record.journal_id.cash_in_sequence_id.next_by_id()
        else:
            if record.journal_id.cash_out_sequence_id:
                values["name"] = record.journal_id.cash_out_sequence_id.next_by_id()
        return values
