# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import base64

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


@tagged("post_install", "-at_install")
class TestAccountEdiUbl(AccountEdiTestCommon):
    @classmethod
    def setUpClass(cls):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)
        cls.env.company.l10n_ro_accounting = True
        cls.currency = cls.env["res.currency"].search([("name", "=", "RON")])
        cls.country_state = cls.env["res.country.state"].search(
            [("name", "=", "Timiș")]
        )
        cls.env.company.write(
            {
                "vat": "RO30834857",
                "name": "FOREST AND BIOMASS ROMANIA S.A.",
                "country_id": cls.env.ref("base.ro").id,
                "currency_id": cls.currency.id,
                "street": "Ferma 5-6",
                "city": "Giulvaz",
                "state_id": cls.country_state.id,
                "zip": "300011",
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "SCOALA GIMNAZIALA COMUNA FOENI",
                "vat": "29152430",
                "country_id": cls.env.ref("base.ro").id,
                "l10n_ro_vat_subjected": True,
                "street": "Foeni Nr. 383",
                "city": "Sat Foeni Com Foeni",
                "state_id": cls.country_state.id,
                "zip": "307175",
                "l10n_ro_e_invoice": True,
            }
        )

        uom_id = cls.env.ref("uom.product_uom_unit").id
        cls.product_a = cls.env["product.product"].create(
            {
                "name": "Bec P21/5W",
                "default_code": "00000623",
                "type": "product",
                "uom_id": uom_id,
                "uom_po_id": uom_id,
            }
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Bec P21/10W",
                "default_code": "00000624",
                "type": "product",
                "uom_id": uom_id,
                "uom_po_id": uom_id,
            }
        )
        cls.tax_19 = cls.env["account.tax"].create(
            {
                "name": "tax_19",
                "amount_type": "percent",
                "amount": 19,
                "type_tax_use": "sale",
                "sequence": 19,
                "company_id": cls.env.company.id,
            }
        )

        cls.invoice = cls.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "name": "FBRAO2092",
                    "partner_id": cls.partner.id,
                    "invoice_date": fields.Date.from_string("2022-09-01"),
                    "currency_id": cls.currency.id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "name": "[00000623] Bec P21/5W",
                                "quantity": 5,
                                "price_unit": 1000.00,
                                "tax_ids": [(6, 0, cls.tax_19.ids)],
                            },
                        ),
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_b.id,
                                "name": "[00000624] Bec P21/10W",
                                "quantity": 5,
                                "price_unit": 1000.00,
                                "tax_ids": [(6, 0, cls.tax_19.ids)],
                            },
                        ),
                    ],
                }
            ]
        )

        cls.expected_invoice_factur_values = """
            <Invoice
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            xmlns:cac=
            "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
                <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
                <cbc:CustomizationID>
                    urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.0
                </cbc:CustomizationID>
                <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
                <cbc:ID>FBRAO2092</cbc:ID>
                <cbc:IssueDate>2022-09-01</cbc:IssueDate>
                <cbc:DueDate>2022-09-01</cbc:DueDate>
                <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
                <cbc:DocumentCurrencyCode>RON</cbc:DocumentCurrencyCode>
                <cbc:BuyerReference>SCOALA GIMNAZIALA COMUNA FOENI</cbc:BuyerReference>
                <cac:OrderReference>
                    <cbc:ID>FBRAO2092</cbc:ID>
                </cac:OrderReference>
                <cac:AccountingSupplierParty>
                    <cac:Party>
                        <cbc:EndpointID schemeID="9947">RO30834857</cbc:EndpointID>
                        <cac:PartyName>
                            <cbc:Name>FOREST AND BIOMASS ROMANIA S.A.</cbc:Name>
                        </cac:PartyName>
                        <cac:PostalAddress>
                            <cbc:StreetName>Ferma 5-6</cbc:StreetName>
                            <cbc:CityName>Giulvaz</cbc:CityName>
                            <cbc:PostalZone>300011</cbc:PostalZone>
                            <cbc:CountrySubentity>RO-TM</cbc:CountrySubentity>
                            <cac:Country>
                                <cbc:IdentificationCode>RO</cbc:IdentificationCode>
                            </cac:Country>
                        </cac:PostalAddress>
                        <cac:PartyTaxScheme>
                            <cbc:CompanyID>RO30834857</cbc:CompanyID>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:PartyTaxScheme>
                        <cac:PartyLegalEntity>
                            <cbc:RegistrationName>
                            FOREST AND BIOMASS ROMANIA S.A.
                            </cbc:RegistrationName>
                            <cbc:CompanyID>RO30834857</cbc:CompanyID>
                        </cac:PartyLegalEntity>
                        <cac:Contact>
                            <cbc:Name>FOREST AND BIOMASS ROMANIA S.A.</cbc:Name>
                        </cac:Contact>
                    </cac:Party>
                </cac:AccountingSupplierParty>
                <cac:AccountingCustomerParty>
                    <cac:Party>
                        <cbc:EndpointID schemeID="9947">29152430</cbc:EndpointID>
                        <cac:PartyName>
                            <cbc:Name>SCOALA GIMNAZIALA COMUNA FOENI</cbc:Name>
                        </cac:PartyName>
                        <cac:PostalAddress>
                            <cbc:StreetName>Foeni Nr. 383</cbc:StreetName>
                            <cbc:CityName>Sat Foeni Com Foeni</cbc:CityName>
                            <cbc:PostalZone>307175</cbc:PostalZone>
                            <cbc:CountrySubentity>RO-TM</cbc:CountrySubentity>
                            <cac:Country>
                                <cbc:IdentificationCode>RO</cbc:IdentificationCode>
                            </cac:Country>
                        </cac:PostalAddress>
                        <cac:PartyTaxScheme>
                            <cbc:CompanyID>29152430</cbc:CompanyID>
                            <cac:TaxScheme>
                                <cbc:ID>!= VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:PartyTaxScheme>
                        <cac:PartyLegalEntity>
                            <cbc:RegistrationName>
                            SCOALA GIMNAZIALA COMUNA FOENI
                            </cbc:RegistrationName>
                            <cbc:CompanyID>29152430</cbc:CompanyID>
                        </cac:PartyLegalEntity>
                        <cac:Contact>
                            <cbc:Name>SCOALA GIMNAZIALA COMUNA FOENI</cbc:Name>
                        </cac:Contact>
                    </cac:Party>
                </cac:AccountingCustomerParty>
                <cac:PaymentMeans>
                    <cbc:PaymentMeansCode name="credit transfer">30</cbc:PaymentMeansCode>
                    <cbc:PaymentID>FBRAO2092</cbc:PaymentID>
                </cac:PaymentMeans>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="RON">1900.00</cbc:TaxAmount>
                    <cac:TaxSubtotal>
                        <cbc:TaxableAmount currencyID="RON">10000.00</cbc:TaxableAmount>
                        <cbc:TaxAmount currencyID="RON">1900.00</cbc:TaxAmount>
                        <cac:TaxCategory>
                            <cbc:ID>S</cbc:ID>
                            <cbc:Percent>19.0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:TaxCategory>
                    </cac:TaxSubtotal>
                </cac:TaxTotal>
                <cac:LegalMonetaryTotal>
                    <cbc:LineExtensionAmount currencyID="RON">10000.00</cbc:LineExtensionAmount>
                    <cbc:TaxExclusiveAmount currencyID="RON">10000.00</cbc:TaxExclusiveAmount>
                    <cbc:TaxInclusiveAmount currencyID="RON">11900.00</cbc:TaxInclusiveAmount>
                    <cbc:PrepaidAmount currencyID="RON">0.00</cbc:PrepaidAmount>
                    <cbc:PayableAmount currencyID="RON">11900.00</cbc:PayableAmount>
                </cac:LegalMonetaryTotal>
                <cac:InvoiceLine>
                    <cbc:ID>1</cbc:ID>
                    <cbc:InvoicedQuantity unitCode="C62">5.0</cbc:InvoicedQuantity>
                    <cbc:LineExtensionAmount currencyID="RON">5000.00</cbc:LineExtensionAmount>
                    <cac:Item>
                        <cbc:Description>[00000623] Bec P21/5W</cbc:Description>
                        <cbc:Name>Bec P21/5W</cbc:Name>
                        <cac:SellersItemIdentification>
                        <cbc:ID>00000623</cbc:ID>
                        </cac:SellersItemIdentification>
                        <cac:ClassifiedTaxCategory>
                            <cbc:ID>S</cbc:ID>
                            <cbc:Percent>19.0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:ClassifiedTaxCategory>
                    </cac:Item>
                    <cac:Price>
                        <cbc:PriceAmount currencyID="RON">1000.00</cbc:PriceAmount>
                        <cbc:BaseQuantity unitCode="C62">5.0</cbc:BaseQuantity>
                    </cac:Price>
                </cac:InvoiceLine>
                <cac:InvoiceLine>
                    <cbc:ID>2</cbc:ID>
                    <cbc:InvoicedQuantity unitCode="C62">5.0</cbc:InvoicedQuantity>
                    <cbc:LineExtensionAmount currencyID="RON">5000.00</cbc:LineExtensionAmount>
                    <cac:Item>
                        <cbc:Description>[00000624] Bec P21/10W</cbc:Description>
                        <cbc:Name>Bec P21/10W</cbc:Name>
                        <cac:SellersItemIdentification>
                            <cbc:ID>00000624</cbc:ID>
                        </cac:SellersItemIdentification>
                        <cac:ClassifiedTaxCategory>
                            <cbc:ID>S</cbc:ID>
                            <cbc:Percent>19.0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:ClassifiedTaxCategory>
                    </cac:Item>
                    <cac:Price>
                        <cbc:PriceAmount currencyID="RON">1000.00</cbc:PriceAmount>
                        <cbc:BaseQuantity unitCode="C62">5.0</cbc:BaseQuantity>
                    </cac:Price>
                </cac:InvoiceLine>
            </Invoice>
        """

    def test_account_edi_ubl(self):
        self.invoice.action_post()
        invoice_xml = self.invoice.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)
        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(
            self.expected_invoice_factur_values
        )
        self.assertXmlTreeEqual(current_etree, expected_etree)
