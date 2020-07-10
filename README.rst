.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Manage an Olive Mill with Odoo
==============================

This project provides modules to run an Olive Mill with `Odoo <https://www.odoo.com/>`_, the leading OpenSource ERP. This project has been initiated by the `Barroux Abbey <https://www.barroux.org/>`_, a benedictine abbey located near the Mont Ventoux in France. The Barroux Abbey owns and operates an olive mill where the olives harvested by the monks and surrounding olive farmers are pressed to produce olive oil. You can discover the olive mill of the Barroux Abbey in `this video <https://boutique.barroux.org/content/9-espace-photos>`_.

The 2018 olive harvest campaign was the first to run with Odoo at the Barroux Abbey and it has been used for all their successive campaigns. So this projet is battle-field tested ! The olive mill of the Barroux abbey is certified to produce **organic** olive oil. So this project supports the management of both organic and non-organic oil productions. The production method used by the Barroux abbey is **lot-by-lot**: each palox is processed separately ; an olive farmer can get back the olive oil from his own olives (if he has filled a palox) and benefit from the yield of this own trees. So the production method implemented by this project is lot-by-lot only.

These modules for the olive mill run above the stock and production modules of Odoo, that support tracability by lot and management of expiry dates. They are also fully integrated with the invoicing/accounting stack of Odoo.

Features
========

Here is a list of features provided by the **olive_mill** module:

* Full tracability from the ochard to the oil bottle,
* Support the production of several different types of olive oil,
* Configuration of parcels and ochards for each olive farmer with their full properties (land registry ref, area, number of trees, planted year, irrigation type, olive variants, ...)
* Configure cultivation methods for each olive farmer (treatments, date of treatment, ...)
* Manage the arrival of olives from olive farmers (weighing, control, ...)
* For each arrival, the olive farmer decides if he wants to get back the oil, or sell it to the olive mill, or a mix of both,
* Manage the press (with first-of-day and last-of-day compensations if the press requires it),
* Handle shrinkage on each press sent to a special shrinkage tank,
* Manage retreival of olive oil (if the farmer wants to get back his olive oil),
* Computation of ratios per press, per arrival, per farmer and per campaign,
* Manage olive tanks (for the olive oil purchased by the olive mill) : stock in each tank, partial transfers, full transfers,
* Manage bottling with lots and expiry dates,
* Generation of nice tracability reports for each lot of oil bottle,
* Auto-generation of both supplier invoice (if the olive farmer sells his olive oil to the mill) and customer invoice (press service per kg of olive, options, packaging, `AFIDOL tax <https://afidol.org/les-cotisations-volontaires-obligatoires/>`_) via the use of pricelists,
* reporting and statistics.

There are several other small features that you can use (or not) :

* pre-campaign polls with olive farmers to build estimates before the campaign starts,
* manage the lending of boxes and palox to olive farmers,
* manage appointments with olive farmers (lending of palox, arrival of olives, retreival of oil, etc.),
* manage oil analysis (peroxide, acidity, etc.),

The module **l10n_fr_olive_mill** adds support for the auto-generation of the monthly `AGRIMER <https://www.franceagrimer.fr/>`_ report for the French agriculture administration.

Odoo version support
====================

The project runs with Odoo community version 10.0 (it should also work with Odoo Enterprise). We plan to port it to Odoo Community version 14.0 (which should be released in October 2020). Of course, you are free to contribute the port to any Odoo version !

Credits
=======

Main author
-----------

* Alexis de Lattre <alexis.delattre@akretion.com>

Contributor
-----------

* Brother Bernard (French translation)
