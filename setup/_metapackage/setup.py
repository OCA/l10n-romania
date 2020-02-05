import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-l10n_ro_account_period_close',
        'odoo13-addon-l10n_ro_fiscal_validation',
        'odoo13-addon-l10n_ro_partner_create_by_vat',
        'odoo13-addon-l10n_ro_partner_unique',
        'odoo13-addon-l10n_ro_vat_on_payment',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
