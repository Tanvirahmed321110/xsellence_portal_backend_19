# -*- coding: utf-8 -*-
from odoo import models


class PendingProjectReport(models.AbstractModel):
    _name = 'report.xsellence_portal.report_pending_project_document'
    _description = 'Pending Project Report'

    def _get_report_values(self, docids, data=None):
        Project = self.env['project.project']

        pending_projects = Project.sudo().search([
            ('custom_status', '=', 'planning'),
        ], order='create_date desc')

        return {
            'doc_ids': docids,
            'doc_model': 'project.project',
            'docs': pending_projects,
            'data': data,
        }