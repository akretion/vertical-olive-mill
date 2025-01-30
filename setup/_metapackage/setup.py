import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-akretion-vertical-olive-mill",
    description="Meta package for akretion-vertical-olive-mill Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-l10n_fr_olive_mill',
        'odoo14-addon-olive_mill',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
