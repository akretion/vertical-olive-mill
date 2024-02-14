# Copyright 2023 Barroux Abbey
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


_column_renames = {
    "product_template": [("olive_type", None)],
    "olive_arrival_line": [("out_invoice_id", None), ("in_invoice_line_id", None)],
}


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_oil' WHERE olive_type='oil'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_tax' WHERE olive_type='tax'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_service' WHERE olive_type='service'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_extra_service' WHERE olive_type='extra_service'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_analysis' WHERE olive_type='analysis'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_bottle_full_pack_phantom' WHERE olive_type='bottle_full_pack_phantom'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_bottle_full_pack' WHERE olive_type='bottle_full_pack'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_bottle_full' WHERE olive_type='bottle_full'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_bottle_empty' WHERE olive_type='bottle' AND type='product'")
    openupgrade.logged_query(env.cr, "UPDATE product_template set detailed_type='olive_barrel_farmer', type='product' WHERE olive_type='bottle' AND type='consu'")
    openupgrade.rename_columns(env.cr, _column_renames)
