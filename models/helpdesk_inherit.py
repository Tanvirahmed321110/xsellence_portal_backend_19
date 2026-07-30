from odoo import models, fields, api

class Helpdesk(models.Model):
    _inherit = 'helpdesk.ticket'
    _order = 'create_date desc'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help='Project related to this ticket'
    )

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

    @api.onchange('project_id')
    def _onchange_project_id_set_customer(self):
        for rec in self:
            rec.partner_id = rec.project_id.partner_id if rec.project_id and rec.project_id.partner_id else False

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
