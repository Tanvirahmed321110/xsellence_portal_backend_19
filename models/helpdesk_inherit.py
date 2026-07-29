from odoo import models, fields, api

class Helpdesk(models.Model):
    _inherit = 'helpdesk.ticket'
    _order = 'create_date desc'

    employee_ids = fields.Many2many(
        'hr.employee',
        string = 'Employees',
        help='Select multiple employees assigned to this ticket'
    )

    assign_date = fields.Datetime(
        string='Assign Date',
        help='Date and time when the ticket was assigned to the employee'
    )

    deadline = fields.Date(
        string='Deadline',
        help='Expected date to resolve/solve this ticket'
    )

    # is_overdue = fields.Boolean(
    #     string='Is Overdue',
    #     compute='_compute_is_overdue',
    #     store=True
    # )
    #
    # @api.depends('deadline')
    # def _compute_is_overdue(self):
    #     today = fields.Date.today()
    #     for rec in self:
    #         rec.is_overdue = bool(rec.deadline and rec.deadline < today)
    #
    # def _cron_update_overdue_tickets(self):
    #     """Daily cron to refresh is_overdue flag for all tickets"""
    #     tickets = self.search([('deadline', '!=', False)])
    #     tickets._compute_is_overdue()