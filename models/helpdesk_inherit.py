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
        string='Employees',
        help='Select multiple employees assigned to this ticket'
    )

    assigned_user_ids = fields.Many2many(
        'res.users',
        string='Assigned Users',
        tracking=True,
        help='Select multiple users assigned to this ticket'
    )

    assign_date = fields.Datetime(
        string='Assign Date',
        default=fields.Datetime.now,
        tracking=True,
        help='Date and time when the ticket was assigned to the employee'
    )

    deadline = fields.Date(
        string='Deadline',
        tracking=True,
        help='Expected date to resolve/solve this ticket'
    )

    @api.onchange('project_id')
    def _onchange_project_id_set_customer(self):
        for rec in self:
            rec.partner_id = rec.project_id.partner_id if rec.project_id and rec.project_id.partner_id else False

    @api.onchange('assigned_user_ids')
    def _onchange_assigned_user_ids_set_primary_user(self):
        for rec in self:
            rec.user_id = rec.assigned_user_ids[:1].id if rec.assigned_user_ids else False

    @api.onchange('employee_ids')
    def _onchange_employee_ids_set_users(self):
        for rec in self:
            linked_users = rec.employee_ids.mapped('user_id')
            rec.assigned_user_ids = [(6, 0, linked_users.ids)]
            rec.user_id = linked_users[:1].id if linked_users else False

    def _default_low_priority_value(self):
        priority_field = self._fields.get('priority')
        selection = []
        if priority_field and priority_field.selection:
            selection = priority_field.selection(self) if callable(priority_field.selection) else priority_field.selection

        selection_keys = [key for key, _label in selection]
        if '0' in selection_keys:
            return '0'

        for key, label in selection:
            if (label or '').strip().casefold() == 'low':
                return key

        return selection_keys[0] if selection_keys else False

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if 'assign_date' in self._fields and not values.get('assign_date'):
            values['assign_date'] = fields.Datetime.now()
        if 'priority' in self._fields and not values.get('priority'):
            low_priority = self._default_low_priority_value()
            if low_priority is not False:
                values['priority'] = low_priority
        return values

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

    def _create_member_change_notifications(self, added_user_ids=None, removed_user_ids=None):
        notification_model = self.env['xsellence.assignment.notification']
        actor_name = self.env.user.name or 'A user'

        for ticket in self:
            if added_user_ids:
                notification_model.create_for_users(added_user_ids, {
                    'title': 'Support Ticket Member Added',
                    'description': '%s added you to %s ticket.' % (actor_name, ticket.name),
                    'view_url': '/helpdesks/ticket_details/%s' % ticket.id,
                    'res_model': 'helpdesk.ticket',
                    'res_id': ticket.id,
                })

            if removed_user_ids:
                notification_model.create_for_users(removed_user_ids, {
                    'title': 'Support Ticket Member Removed',
                    'description': '%s removed you from %s ticket.' % (actor_name, ticket.name),
                    'view_url': '/helpdesks/ticket_details/%s' % ticket.id,
                    'res_model': 'helpdesk.ticket',
                    'res_id': ticket.id,
                })

    def _prepare_assignment_values(self, vals):
        updated_vals = dict(vals)

        if updated_vals.get('project_id'):
            project = self.env['project.project'].browse(updated_vals['project_id'])
            updated_vals['partner_id'] = project.partner_id.id if project.partner_id else False

        if 'assign_date' in self._fields and not updated_vals.get('assign_date'):
            updated_vals['assign_date'] = fields.Datetime.now()

        if 'priority' in self._fields and not updated_vals.get('priority'):
            low_priority = self._default_low_priority_value()
            if low_priority is not False:
                updated_vals['priority'] = low_priority

        employee_commands = updated_vals.get('employee_ids')
        if employee_commands is not None:
            employee_ids = self._resolve_m2m_commands(employee_commands)
            employees = self.env['hr.employee'].browse(employee_ids)
            linked_user_ids = employees.mapped('user_id').ids
            updated_vals['assigned_user_ids'] = [(6, 0, linked_user_ids)]
            updated_vals['user_id'] = linked_user_ids[0] if linked_user_ids else False

        assigned_user_commands = updated_vals.get('assigned_user_ids')
        if assigned_user_commands is not None:
            assigned_user_ids = self._resolve_m2m_commands(assigned_user_commands)
            if assigned_user_ids:
                updated_vals['user_id'] = assigned_user_ids[0]
            else:
                updated_vals['user_id'] = False
        elif updated_vals.get('user_id'):
            updated_vals['assigned_user_ids'] = [(4, updated_vals['user_id'])]
            if 'employee_ids' not in updated_vals:
                employee_ids = self.env['hr.employee'].search([('user_id', '=', updated_vals['user_id'])]).ids
                updated_vals['employee_ids'] = [(6, 0, employee_ids)]

        return updated_vals

    @staticmethod
    def _resolve_m2m_commands(commands):
        resolved_ids = []
        if not isinstance(commands, list):
            return resolved_ids

        for command in commands:
            if not isinstance(command, (list, tuple)) or not command:
                continue
            operation = command[0]
            if operation == 6 and len(command) > 2 and isinstance(command[2], list):
                resolved_ids = [int(user_id) for user_id in command[2] if user_id]
            elif operation == 4 and len(command) > 1 and command[1]:
                resolved_ids.append(int(command[1]))
            elif operation == 5:
                resolved_ids = []

        deduped_ids = []
        seen_ids = set()
        for user_id in resolved_ids:
            if user_id in seen_ids:
                continue
            seen_ids.add(user_id)
            deduped_ids.append(user_id)
        return deduped_ids

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._prepare_assignment_values(vals) for vals in vals_list]
        tickets = super().create(vals_list)

        for ticket in tickets:
            assigned_user_ids = set(ticket.user_id.ids + ticket.assigned_user_ids.ids)
            if assigned_user_ids:
                ticket._create_assignment_notifications(assigned_user_ids)

        return tickets

    def write(self, vals):
        old_user_map = {
            ticket.id: set(ticket.user_id.ids + ticket.assigned_user_ids.ids)
            for ticket in self
        }
        vals = self._prepare_assignment_values(vals)

        result = super().write(vals)

        if 'user_id' in vals or 'assigned_user_ids' in vals:
            for ticket in self:
                new_user_ids = set(ticket.user_id.ids + ticket.assigned_user_ids.ids)
                old_user_ids = old_user_map.get(ticket.id, set())
                added_user_ids = new_user_ids - old_user_ids
                removed_user_ids = old_user_ids - new_user_ids

                if added_user_ids:
                    ticket._create_assignment_notifications(added_user_ids)
                    ticket._create_member_change_notifications(added_user_ids=added_user_ids)

                if removed_user_ids:
                    ticket._create_member_change_notifications(removed_user_ids=removed_user_ids)

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
