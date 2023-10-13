# Copyright 2023 Barroux Abbey
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copied and adapted from the OCA module intrastat_product

from openupgradelib import openupgrade  # pylint: disable=W7936


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.table_exists(env.cr, "account_invoice_line"):
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE olive_arrival_line oal
            SET in_invoice_line_id = aml.id
            FROM account_invoice_line ail
            JOIN account_move_line aml ON aml.old_invoice_line_id = ail.id
            WHERE oal.%(old_in_invoice_line_id)s = ail.id"""
            % {"old_in_invoice_line_id": openupgrade.get_legacy_name("in_invoice_line_id")},
        )
    if openupgrade.table_exists(env.cr, "account_invoice"):
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE olive_arrival_line oal
            SET out_invoice_id = am.id
            FROM account_invoice ai
            JOIN account_move am ON am.old_invoice_id = ai.id
            WHERE oal.%(old_out_invoice_id)s = ai.id"""
            % {"old_out_invoice_id": openupgrade.get_legacy_name("out_invoice_id")},
        )
