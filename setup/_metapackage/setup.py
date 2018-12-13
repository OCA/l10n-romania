import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-currency_rate_update_RO_BNR',
        'odoo11-addon-l10n_ro_account_bank_statement_import_mt940_brd',
        'odoo11-addon-l10n_ro_account_period_close',
        'odoo11-addon-l10n_ro_address_extended',
        'odoo11-addon-l10n_ro_config',
        'odoo11-addon-l10n_ro_fiscal_validation',
        'odoo11-addon-l10n_ro_hr',
        'odoo11-addon-l10n_ro_hr_contract',
        'odoo11-addon-l10n_ro_partner_create_by_vat',
        'odoo11-addon-l10n_ro_partner_unique',
        'odoo11-addon-l10n_ro_report_D300',
        'odoo11-addon-l10n_ro_report_trial_balance',
        'odoo11-addon-l10n_ro_siruta',
        'odoo11-addon-l10n_ro_vat_on_payment',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
