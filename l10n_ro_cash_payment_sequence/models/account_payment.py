from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_out_number = fields.Char(
        "Cash seq number",
        default="",
        help="""If is a cache out payment will have a number given from the
      sequence from cache journal or next number ( from last date/id)
      If you are the account manger, you can see this field and you can modify it.
      It you modify it, the payment will have this number.
      If no number at the end of sequence (and no cache journal in sequence)
      will start from default C0001
      """,
        tracking=1,
    )
    name = fields.Char(
        compute="_compute_payment_name",
        store=1,
        help="computed name as payment_out_number if exist,"
        " if not will be the name from move_id",
        tracking=1,
    )
    type = fields.Selection(related="journal_id.type", store=1, readonly=1)

    @api.depends("payment_out_number", "move_id", "move_id.name")
    def _compute_payment_name(self):
        for rec in self:
            if rec.state == "draft":
                rec.name = ""
            elif rec.payment_out_number:
                rec.name = rec.payment_out_number
            else:
                rec.name = rec.move_id.name

    def action_post(self):
        super(AccountPayment, self).action_post()
        self.set_payment_out_number()

    def set_payment_out_number(self):
        # force cash in/out sequence
        for payment in self:
            if (
                not payment.payment_out_number
                and not payment.is_internal_transfer
                and payment.partner_type == "customer"
                and payment.journal_id.type == "cash"
            ):
                if payment.payment_type == "inbound":
                    if payment.journal_id.cash_in_sequence_id:
                        payment.payment_out_number = (
                            payment.journal_id.cash_in_sequence_id.next_by_id()
                        )
                    else:
                        last_cache_payment = self.search(
                            [
                                ("state", "=", "posted"),
                                ("is_internal_transfer", "!=", True),
                                ("journal_id", "=", payment.journal_id.id),
                                ("partner_type", "=", "customer"),
                                ("payment_out_number", "!=", ""),
                            ],
                            limit=1,
                            order="date desc, id desc",
                        )
                        if last_cache_payment:
                            last_payment_out_number = (
                                last_cache_payment.payment_out_number.rstrip()
                            )
                            _index = 0
                            for _index, c in enumerate(last_payment_out_number[::-1]):
                                if not c.isdigit():
                                    break
                            index = _index  # fuck  OCA flake 8 rules
                            if index != 0:
                                padding = index
                                nr = str(
                                    int(
                                        last_payment_out_number[
                                            len(last_payment_out_number) - index :
                                        ]
                                    )
                                    + 1
                                )
                                final_padding = padding - len(nr)
                                leading_zero = ""
                                if final_padding > 1:
                                    leading_zero = "0" * final_padding
                                payment.payment_out_number = (
                                    last_payment_out_number[
                                        0 : len(last_payment_out_number) - index
                                    ]
                                    + leading_zero
                                    + f"{nr}"
                                )
                            else:
                                payment.payment_out_number = "C0001"

                        else:
                            payment.payment_out_number = "C0001"
