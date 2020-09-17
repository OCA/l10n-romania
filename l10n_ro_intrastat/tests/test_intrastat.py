# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestIntrastat(TransactionCase):
    def setUp(self):
        super(TestIntrastat, self).setUp()
        self.env.user.company_id.write({"vat": "RO20603502"})
        self.intrastat = self.env["account.intrastat.code"].create(
            {"name": "test", "code": "84221100", "suppl_unit_code": "p/st"}
        )

        self.product_1 = self.env["product.product"].create(
            {
                "name": "Test intrastat",
                "invoice_policy": "order",
                "intrastat_id": self.intrastat.id,
            }
        )

        self.product_2 = self.env["product.product"].create(
            {
                "name": "Test intrastat",
                "invoice_policy": "order",

            }
        )

    def test_name(self):
        intrastat = self.env["account.intrastat.code"]._name_search("84221100")
        self.assertEqual(self.intrastat.id, intrastat[0][0])

        self.product_1.categ_id.search_intrastat_code()


    def test_invoice_purchase(self):
        country = self.env.ref("base.de")
        partner_de = self.env["res.partner"].create(
            {"name": "TEST Vendor", "country_id": country.id}
        )

        invoice = Form(self.env["account.move"].with_context(default_type="in_invoice"))
        invoice.partner_id = partner_de
        invoice.intrastat_transaction_id = self.env.ref(
            "l10n_ro_intrastat.intrastat_transaction_1_1"
        )
        invoice.transport_mode_id = self.env.ref("l10n_ro_intrastat.intrastat_trmode_3")
        invoice.invoice_incoterm_id = self.env.ref("account.incoterm_EXW")

        with invoice.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_1
            line_form.price_unit = 10
            line_form.quantity = 20

        invoice = invoice.save()
        invoice.post()

        # a facut onchange ?
        self.assertEqual(invoice.intrastat_country_id, country)

        wizard = Form(self.env["l10n_ro_intrastat.intrastat_xml_declaration"])
        wizard.contact_id = self.env.user.partner_id
        wizard = wizard.save()
        wizard.create_xml()

    def test_invoice_sale(self):
        country = self.env.ref("base.de")
        partner_de = self.env["res.partner"].create(
            {"name": "TEST Customer", "country_id": country.id}
        )

        so = Form(self.env["sale.order"])
        so.partner_id = partner_de

        with so.order_line.new() as so_line:
            so_line.product_id = self.product_1
            so_line.product_uom_qty = 10
            so_line.price_unit = 50

        so = so.save()
        so.action_confirm()
        invoice = so._create_invoices(final=True)
        invoice = Form(invoice)
        invoice.intrastat_transaction_id = self.env.ref(
            "l10n_ro_intrastat.intrastat_transaction_1_1"
        )
        invoice.transport_mode_id = self.env.ref("l10n_ro_intrastat.intrastat_trmode_3")
        invoice.invoice_incoterm_id = self.env.ref("account.incoterm_EXW")

        invoice = invoice.save()
        invoice.post()

        wizard = Form(self.env["l10n_ro_intrastat.intrastat_xml_declaration"])
        wizard.contact_id = self.env.user.partner_id
        wizard.type = "dispatches"
        wizard = wizard.save()
        wizard.create_xml()

    def test_error(self):
        country = self.env.ref("base.de")
        partner_de = self.env["res.partner"].create(
            {"name": "TEST Vendor", "country_id": country.id}
        )

        invoice = Form(self.env["account.move"].with_context(default_type="in_invoice"))
        invoice.partner_id = partner_de

        with invoice.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_2
            line_form.price_unit = 10
            line_form.quantity = 20

        invoice = invoice.save()
        invoice.post()


        wizard = Form(self.env["l10n_ro_intrastat.intrastat_xml_declaration"])
        wizard.contact_id = self.env.user.partner_id
        wizard = wizard.save()

        with self.assertRaises(UserError):
            wizard.create_xml()

        intrastat_transaction = self.env.ref(
            "l10n_ro_intrastat.intrastat_transaction_1_1"
        )
        invoice.write({
            'intrastat_transaction_id':intrastat_transaction.id
        })
        with self.assertRaises(UserError):
            wizard.create_xml()

        transport_mode = self.env.ref("l10n_ro_intrastat.intrastat_trmode_3")
        invoice.write({
            'transport_mode_id': transport_mode.id
        })
        with self.assertRaises(UserError):
            wizard.create_xml()

        invoice_incoterm = self.env.ref("account.incoterm_EXW")
        invoice.write({
            'invoice_incoterm_id': invoice_incoterm.id
        })
        with self.assertRaises(UserError):
            wizard.create_xml()

