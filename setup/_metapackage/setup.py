import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-currency_rate_update_RO_BNR>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_anaf_sync>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_alpha>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_base>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_bcr>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_brd>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_ing>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_import_mt940_rffsn>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_bank_statement_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_edi_ubl>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_edit_currency_rate>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_period_close>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_account_report_invoice>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_city>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_config>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_dvi>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_etransport>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_fiscal_validation>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_nondeductible_vat>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_partner_create_by_vat>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_partner_unique>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_payment_receipt_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_payment_to_statement>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_pos>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_date>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_date_wizard>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_mrp>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_notice>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_account_reception_in_progress>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_picking_comment_template>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_picking_valued_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_price_difference>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_stock_report>=16.0dev,<16.1dev',
        'odoo-addon-l10n_ro_vat_on_payment>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
