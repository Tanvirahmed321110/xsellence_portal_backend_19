from odoo import models, fields, api

class Helpdesk(models.Model):
    _inherit = 'helpdesk.ticket'
    _order = 'create_date desc'

    employee_ids = fields.Many2many(
        'hr.employee',
        string = 'Employees',
        help='Select multiple employees assigned to this ticket'
    )