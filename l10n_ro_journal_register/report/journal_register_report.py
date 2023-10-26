# ©  2023 Deltatech
# See README.rst file on addons root folder for license details


from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class JournalRegisterReport(models.TransientModel):
    _name = "l10n.ro.journal.register.report"
    _description = "JournalRegisterReport"

    date_from = fields.Date(
        string="Start Date", required=True, default=fields.Date.today
    )
    date_to = fields.Date(string="End Date", required=True, default=fields.Date.today)

    in_red = fields.Boolean()
    journal_ids = fields.Many2many("account.journal", string="Journals")
    result = fields.Html(string="Result Export", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super(JournalRegisterReport, self).default_get(fields_list)
        today = fields.Date.context_today(self)
        today = fields.Date.from_string(today)

        from_date = today + relativedelta(day=1, months=0, days=0)
        to_date = today + relativedelta(day=1, months=1, days=-1)

        res["date_from"] = fields.Date.to_string(from_date)
        res["date_to"] = fields.Date.to_string(to_date)

        return res

    def button_show(self):
        self.ensure_one()

        if self.journal_ids:
            account_move_ids = self.env["account.move"].search(
                [
                    ("date", ">=", self.date_from),
                    ("date", "<=", self.date_to),
                    ("move_type", "=", "entry"),
                    ("journal_id", "in", self.journal_ids.ids),
                    ("company_id", "=", self.company_id.id),
                ]
            )
        else:
            account_move_ids = self.env["account.move"].search(
                [
                    ("date", ">=", self.date_from),
                    ("date", "<=", self.date_to),
                    ("move_type", "=", "entry"),
                    ("company_id", "=", self.company_id.id),
                ]
            )

        # account.invoice
        invoice_in_ids = self.env["account.move"].search(
            [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("move_type", "in", ["in_invoice", "in_refund", "in_receipt"]),
                ("company_id", "=", self.company_id.id),
            ]
        )

        # account.invoice
        invoice_out_ids = self.env["account.move"].search(
            [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("company_id", "=", self.company_id.id),
            ]
        )

        self.extract_invoice_in(invoice_in_ids)
        self.extract_invoice_out(invoice_out_ids)
        self.extract_account_move(account_move_ids)

        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_journal_register.action_journal_register_report_line"
        )
        return action

    def fix_debit_credit(self, cont_d, cont_c, value_d, value_c, in_red):

        value = value_d - value_c

        if value < 0 and not in_red:
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        if in_red:
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = -value_d, -value_c

        if cont_c.code[:4] == "4111" and cont_d.code[0] != "5":
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        if cont_d.code[:3] == "401" and cont_c.code[0] != "5":
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        if cont_c.code[0] == "6" and cont_c.code[:3] != "609":
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        if cont_d.code[0] == "7" and cont_d.code[:3] != "709":
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        if cont_d.code[:3] == "609":
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        if cont_c.code[:3] == "709":
            cont_d, cont_c = cont_c, cont_d
            value_d, value_c = value_c, value_d

        return cont_d, cont_c, value_d, value_c

    def extract_invoice_in(self, invoice_in_ids):
        report_lines_values = []
        for invoice in invoice_in_ids:

            cont_p = False
            for line in invoice.line_ids:
                if line.account_id.user_type_id.type in ("receivable", "payable"):
                    cont_p = line.account_id

            for line in invoice.line_ids.filtered(lambda m: not m.display_type):
                cont_l = line.account_id
                if cont_l == cont_p:
                    continue

                report_line = {
                    "report_id": self.id,
                    "move_id": invoice.id,
                    "date": invoice.invoice_date,
                    "journal_id": invoice.journal_id.id,
                    "debit_account_id": cont_l.id,
                    "credit_account_id": cont_p.id,
                    "debit": line.debit,
                    "credit": line.credit,
                    "product_id": line.product_id.id,
                    "quantity": line.quantity,
                    "partner_id": invoice.partner_id.id,
                    "move_type": invoice.move_type,
                }

                in_red = False
                if self.in_red and invoice.move_type and "refund" in invoice.move_type:
                    in_red = True

                cont_c = cont_p
                cont_d = cont_l
                value_d = line.debit
                value_c = line.credit

                cont_d, cont_c, value_d, value_c = self.fix_debit_credit(
                    cont_d, cont_c, value_d, value_c, in_red
                )

                report_line["debit_account_id"] = cont_d.id
                report_line["credit_account_id"] = cont_c.id
                report_line["debit"] = value_d
                report_line["credit"] = value_c
                report_line["balance"] = value_d - value_c
                report_lines_values.append(report_line)

        self.env["l10n.ro.journal.register.report.line"].create(report_lines_values)

    def extract_invoice_out(self, invoice_out_ids):
        report_lines_values = []
        for invoice in invoice_out_ids:
            cont_p = False
            for line in invoice.line_ids:
                if line.account_id.user_type_id.type in ("receivable", "payable"):
                    cont_p = line.account_id

            for line in invoice.line_ids.filtered(lambda m: not m.display_type):
                cont_l = line.account_id
                if cont_l == cont_p:
                    continue

                report_line = {
                    "report_id": self.id,
                    "move_id": invoice.id,
                    "date": invoice.invoice_date,
                    "journal_id": invoice.journal_id.id,
                    "debit_account_id": cont_l.id,
                    "credit_account_id": cont_p.id,
                    "debit": line.debit,
                    "credit": line.credit,
                    "product_id": line.product_id.id,
                    "quantity": line.quantity,
                    "partner_id": invoice.partner_id.id,
                    "move_type": invoice.move_type,
                }

                in_red = False

                if self.in_red and invoice.move_type and "refund" in invoice.move_type:
                    in_red = True

                cont_d = cont_p
                cont_c = cont_l

                value_d = line.debit
                value_c = line.credit

                cont_d, cont_c, value_d, value_c = self.fix_debit_credit(
                    cont_d, cont_c, value_d, value_c, in_red
                )

                report_line["debit_account_id"] = cont_d.id
                report_line["credit_account_id"] = cont_c.id
                report_line["debit"] = value_d
                report_line["credit"] = value_c
                report_line["balance"] = value_d - value_c
                report_lines_values.append(report_line)

        self.env["l10n.ro.journal.register.report.line"].create(report_lines_values)

    def extract_account_move(self, account_move_ids):
        report_lines_values = []

        domain = [("name", "=", "l10n_ro_stock_account"), ("state", "=", "installed")]
        l10n_ro_stock_account = self.env["ir.module.module"].sudo().search(domain)

        for move in account_move_ids:

            lines = move.line_ids.filtered(lambda m: not m.display_type)
            if not lines:
                continue
            line = lines[-1]
            cont_p = line.account_id

            move_type = move.move_type

            if l10n_ro_stock_account:
                for svl in move.stock_valuation_layer_ids:
                    # este necesar sa fe instalat modulul l10n_ro_stock_account
                    move_type = svl.l10n_ro_valued_type

                if (
                    not move_type
                ):  # evaluari de stoc netratate prin l10n_ro_stock_account
                    move_type = move.move_type

            if move_type == "entry" and "POSS" in move.name:
                move_type = "pos_sale"

            if move_type == "entry" and move.ref == "Cash collection":
                move_type = "cash_collection"

            if move_type == "entry" and move.ref == "Payment disposal":
                move_type = "payment_disposal"

            if move.payment_id:
                move_type = "payment_" + move.payment_id.payment_type

            for line in lines:
                cont_l = line.account_id
                if cont_l == cont_p:
                    continue

                report_line = {
                    "report_id": self.id,
                    "move_id": move.id,
                    "date": move.invoice_date,
                    "journal_id": move.journal_id.id,
                    "debit_account_id": cont_l.id,
                    "credit_account_id": cont_p.id,
                    "debit": line.debit,
                    "credit": line.credit,
                    "product_id": line.product_id.id,
                    "quantity": line.quantity,
                    "partner_id": move.partner_id.id,
                    "move_type": move_type,
                }

                if move_type == "pos_sale" and cont_l.code[:4] == "4111":
                    # 4111 nu trebuie sa fie pe Credit ci trebuie
                    # conturile sa fie inversate si suma negativa
                    move_type = "pos_sale_return"

                in_red = False
                if move_type and "return" in move_type:
                    in_red = True

                if cont_l.code[:3] == "408" and cont_p.code[:4] != "4111":
                    in_red = True

                cont_d = cont_l
                cont_c = cont_p
                value = line.debit - line.credit
                if not value:
                    continue
                value_d = line.debit
                value_c = line.credit

                if not self.in_red:
                    in_red = False

                cont_d, cont_c, value_d, value_c = self.fix_debit_credit(
                    cont_d, cont_c, value_d, value_c, in_red
                )

                report_line["debit_account_id"] = cont_d.id
                report_line["credit_account_id"] = cont_c.id
                report_line["debit"] = value_d
                report_line["credit"] = value_c
                report_line["balance"] = value_d - value_c
                report_lines_values.append(report_line)

        self.env["l10n.ro.journal.register.report.line"].create(report_lines_values)


class JournalRegisterReportLine(models.TransientModel):
    _name = "l10n.ro.journal.register.report.line"
    _description = "JournalRegisterReportLine"

    name = fields.Char()
    report_id = fields.Many2one("l10n.ro.journal.register.report", string="Report")
    move_id = fields.Many2one("account.move", string="Move")
    date = fields.Date()
    journal_id = fields.Many2one("account.journal", string="Journal")
    debit_account_id = fields.Many2one("account.account", string="Debit Account")
    debit_code = fields.Char(related="debit_account_id.code", string="Debit Code")
    credit_account_id = fields.Many2one("account.account", string="Credit Account")
    credit_code = fields.Char(related="credit_account_id.code", string="Credit Code")
    debit = fields.Monetary(string="Debit amount")
    credit = fields.Monetary(string="Credit amount")
    balance = fields.Monetary()
    product_id = fields.Many2one("product.product", string="Product")
    quantity = fields.Float()
    partner_id = fields.Many2one("res.partner", string="Partner")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    move_type = fields.Char()
