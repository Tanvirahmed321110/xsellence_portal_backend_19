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

    def _create_assignment_notifications(self, user_ids):
        notification_model = self.env['xsellence.assignment.notification']
        actor_name = self.env.user.name or 'A user'

        for ticket in self:
            notification_model.create_for_users(user_ids, {
                'title': 'Support Ticket Assigned',
                'description': '%s assigned you to %s ticket.' % (actor_name, ticket.name),
                'view_url': '/helpdesks/ticket_details/%s' % ticket.id,
                'res_model': 'helpdesk.ticket',
                'res_id': ticket.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)

        for ticket in tickets:
            if ticket.user_id:
                ticket._create_assignment_notifications([ticket.user_id.id])

        return tickets

    def write(self, vals):
        old_user_map = {
            ticket.id: ticket.user_id.id
            for ticket in self
        }

        result = super().write(vals)

        if 'user_id' in vals:
            for ticket in self:
                old_user_id = old_user_map.get(ticket.id)
                new_user_id = ticket.user_id.id if ticket.user_id else False

                if new_user_id and new_user_id != old_user_id:
                    ticket._create_assignment_notifications([new_user_id])

        return result

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
