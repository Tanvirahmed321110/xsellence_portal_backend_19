from odoo import models


class UserReport(models.AbstractModel):
    _name = 'report.xsellence_portal.user_report_template'
    _description = 'User Report'

    def _get_report_values(self, docids, data=None):
        docids = docids or self.env.context.get('active_ids', [])
        docs = self.env['res.users'].browse(docids).exists().sorted(lambda user: (user.name or '').lower())

        return {
            'doc_ids': docs.ids,
            'doc_model': 'res.users',
            'docs': docs,
        }
