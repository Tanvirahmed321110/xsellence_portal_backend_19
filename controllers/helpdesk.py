from odoo import http
from odoo.http import request
from datetime import date
from ..utilitis.pagination import get_pager

class XsellencePortalHelpdesk(http.Controller):
    def _can_manage_employee_filter(self):
        user = request.env.user
        return (
            user.has_group('xsellence_portal.group_project_manager')
            or user.has_group('xsellence_portal.group_admin')
        )

    def _current_employee(self, user=None):
        user = user or request.env.user
        return request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)],
            limit=1,
        )

    def _selected_employee_scope(self, selected_employee):
        if not selected_employee:
            return request.env['hr.employee'].sudo().browse()
        if selected_employee.user_id:
            return request.env['hr.employee'].sudo().search(
                [('user_id', '=', selected_employee.user_id.id), ('active', '=', True)],
                order='id asc',
            )
        return selected_employee

    def _resolve_selected_employee(self, raw_employee_id):
        user = request.env.user
        current_employee = self._current_employee(user)
        selected_employee_id = int(raw_employee_id or 0)

        if not self._can_manage_employee_filter():
            return current_employee, current_employee.id if current_employee else 0

        if selected_employee_id:
            employee = request.env['hr.employee'].sudo().browse(selected_employee_id)
            if employee.exists():
                return employee, employee.id

        return current_employee, current_employee.id if current_employee else 0

    @staticmethod
    def _ticket_priorities(ticket_model):
        field = ticket_model._fields.get('priority')
        if not field or not field.selection:
            return []
        selection = field.selection
        return selection(ticket_model) if callable(selection) else selection

    @staticmethod
    def _parse_portal_date(raw_value):
        if not raw_value:
            return False
        try:
            return date.fromisoformat(str(raw_value).strip())
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _default_low_priority(priorities):
        priority_keys = [key for key, _label in priorities]
        if '0' in priority_keys:
            return '0'
        for key, label in priorities:
            if (label or '').strip().casefold() == 'low':
                return key
        return priority_keys[0] if priority_keys else False

    @staticmethod
    def _get_visible_ticket_domain(user, employees=False, target_user=False):
        employees = employees or request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)],
        )
        target_user = target_user or user

        domain = ['|', ('user_id', '=', target_user.id), ('assigned_user_ids', 'in', [target_user.id])]
        if employees:
            domain = ['|'] + domain + [('employee_ids', 'in', employees.ids)]

        return domain

    @http.route('/helpdesks', type='http', auth='user', website=True)
    def helpdesk_f(self, **kw):
        user = request.env.user
        Ticket = request.env['helpdesk.ticket'].sudo()
        selected_employee, selected_employee_id = self._resolve_selected_employee(kw.get('employee_id'))
        selected_employee_scope = self._selected_employee_scope(selected_employee)
        target_user = selected_employee.user_id if selected_employee and selected_employee.user_id else user
        domain = self._get_visible_ticket_domain(user, selected_employee_scope, target_user)
        search = (kw.get('search') or '').strip()
        selected_project_id = int(kw.get('project_id') or 0)
        selected_stage_id = int(kw.get('stage_id') or 0)

        if selected_project_id and 'project_id' in Ticket._fields:
            domain.append(('project_id', '=', selected_project_id))
        if selected_stage_id:
            domain.append(('stage_id', '=', selected_stage_id))
        if search:
            if search.isdigit():
                domain += ['|', '|', ('name', 'ilike', search), ('ticket_ref', 'ilike', search), ('id', '=', int(search))]
            else:
                domain += ['|', ('name', 'ilike', search), ('ticket_ref', 'ilike', search)]

        per_page = int(kw.get('per_page', 16))
        total = Ticket.search_count(domain)
        pager = get_pager(
            url='/helpdesks',
            total=total,
            page=kw.get('page', 1),
            per_page=per_page,
            url_args={
                'search': search,
                'employee_id': selected_employee_id if selected_employee_id else '',
                'project_id': selected_project_id if selected_project_id else '',
                'stage_id': selected_stage_id if selected_stage_id else '',
            },
        )

        all_tickets = Ticket.search(domain, order='create_date desc')
        tickets = Ticket.search(
            domain,
            order='create_date desc',
            offset=pager['offset'],
            limit=pager['per_page'],
        )

        projects = request.env['project.project'].sudo().browse()
        if 'project_id' in Ticket._fields:
            projects = all_tickets.mapped('project_id')

        stages = request.env['helpdesk.stage'].sudo().search([], order='name asc')

        tickets_new = all_tickets.filtered(lambda ticket: ticket.stage_id.name == 'New')
        tickets_in_progress = all_tickets.filtered(lambda ticket: ticket.stage_id.name == 'In Progress')
        tickets_solved = all_tickets.filtered(lambda t: t.stage_id.name == 'Solved')
        tickets_cancelled = all_tickets.filtered(lambda t: t.stage_id.name == 'Cancelled')

        return request.render('xsellence_portal.helpdesk_page', {
            'active_menu': 'helpdesk',
            'tickets': tickets,
            'tickets_new': tickets_new,
            'tickets_in_progress': tickets_in_progress,
            'tickets_solved': tickets_solved,
            'tickets_cancelled': tickets_cancelled,
            'count_new': len(tickets_new),
            'count_in_progress': len(tickets_in_progress),
            'count_solved': len(tickets_solved),
            'count_cancelled': len(tickets_cancelled),
            'pager': pager,
            'projects': projects,
            'stages': stages,
            'search': search,
            'selected_employee_id': selected_employee_id,
            'selected_project_id': selected_project_id,
            'selected_stage_id': selected_stage_id,
        })

    # ========================
    # Helpdesk ticket details
    # ========================
    @http.route('/helpdesks/ticket_details/<int:ticket_id>', type='http', auth='user', website=True)
    def ticket_details_f(self, ticket_id,**kw):
        selected_employee_id = int(kw.get('employee_id') or 0)
        employee_query = f'?employee_id={selected_employee_id}' if selected_employee_id else ''
        selected_employee, _selected_employee_id = self._resolve_selected_employee(selected_employee_id)
        selected_employee_scope = self._selected_employee_scope(selected_employee)
        target_user = selected_employee.user_id if selected_employee and selected_employee.user_id else request.env.user
        ticket = request.env['helpdesk.ticket'].sudo().search(
            [('id', '=', ticket_id)] + self._get_visible_ticket_domain(request.env.user, selected_employee_scope, target_user),
            limit=1,
        )
        if not ticket.exists():
            return request.redirect('/helpdesks')


        return request.render('xsellence_portal.ticket_details_page', {
            'active_menu': 'helpdesk',
            'ticket': ticket,
            'selected_employee_id': selected_employee_id,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': f'/dashboard{employee_query}' if employee_query else '/dashboard'},
                {'name': 'Helpdesks', 'url': f'/helpdesks{employee_query}' if employee_query else '/helpdesks'},
                {'name': 'Ticket Details', 'url': False},
            ],
        })

    # ========================
    # Ticket Stage Update
    # ========================
    @http.route('/helpdesks/update_stage', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def update_helpdesk_stage(self, **post):
        ticket_id = int(post.get('ticket_id') or 0)
        stage_id = int(post.get('stage_id') or 0)
        selected_employee_id = int(post.get('employee_id') or 0)
        employee_query = f'?employee_id={selected_employee_id}' if selected_employee_id else ''
        selected_employee, _selected_employee_id = self._resolve_selected_employee(selected_employee_id)
        selected_employee_scope = self._selected_employee_scope(selected_employee)
        target_user = selected_employee.user_id if selected_employee and selected_employee.user_id else request.env.user

        ticket = request.env['helpdesk.ticket'].sudo().search(
            [('id', '=', ticket_id)] + self._get_visible_ticket_domain(request.env.user, selected_employee_scope, target_user),
            limit=1,
        )
        if ticket.exists() and stage_id:
            ticket.write({'stage_id': stage_id})

        return request.redirect(f'/helpdesks/ticket_details/{ticket_id}{employee_query}')


    # ========================
    # Create ticket page
    # ========================
    @http.route('/helpdesks/create_ticket', type='http', auth='user', website=True, methods=['GET'])
    def create_ticket_page(self, **kw):
        Ticket = request.env['helpdesk.ticket'].sudo()
        Team = request.env['helpdesk.team'].sudo()
        teams = Team.search([], order='name asc')

        return request.render('xsellence_portal.create_ticket_page', {
            'active_menu': 'helpdesk',
            'employees': request.env['hr.employee'].sudo().search(
                [('active', '=', True)],
                order='name asc',
            ),
            'teams': teams,
            'projects': request.env['project.project'].sudo().search(
                [('active', '=', True)],
                order='name asc',
            ),
            'priorities': self._ticket_priorities(Ticket),
            'today': date.today().strftime('%Y-%m-%d'),
            'has_project_field': 'project_id' in Ticket._fields,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Helpdesk', 'url': '/helpdesks'},
                {'name': 'Create Ticket', 'url': False},
            ],
        })

    # ========================
    # Submit ticket
    # ========================
    @http.route(
        '/helpdesks/create_ticket/submit',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def submit_ticket(self, **post):
        Ticket = request.env['helpdesk.ticket'].sudo()
        priorities = self._ticket_priorities(Ticket)
        default_priority = self._default_low_priority(priorities)

        subject = (post.get('name') or '').strip()
        if not subject:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Ticket Subject Required',
                'error_desc': 'Enter a subject before submitting the support ticket.',
                'error_btn_label': 'Go Back',
                'error_btn_url': '/helpdesks/create_ticket',
            })

        project_id = int(post.get('project_id') or 0)
        if not project_id:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Project Required',
                'error_desc': 'Select a project before submitting the support ticket.',
                'error_btn_label': 'Go Back',
                'error_btn_url': '/helpdesks/create_ticket',
            })

        employee_ids = [int(employee_id) for employee_id in request.httprequest.form.getlist('employee_ids') if str(employee_id).isdigit()]
        if not employee_ids:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Assignee Required',
                'error_desc': 'Select at least one assignee before submitting the support ticket.',
                'error_btn_label': 'Go Back',
                'error_btn_url': '/helpdesks/create_ticket',
            })
        employees = request.env['hr.employee'].sudo().browse(employee_ids).exists()
        assignee_ids = employees.mapped('user_id').ids

        ticket_deadline = self._parse_portal_date(post.get('deadline'))
        if not ticket_deadline:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Deadline Required',
                'error_desc': 'Enter a valid deadline before submitting the support ticket.',
                'error_btn_label': 'Go Back',
                'error_btn_url': '/helpdesks/create_ticket',
            })
        if ticket_deadline < date.today():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Invalid Deadline',
                'error_desc': 'Deadline cannot be earlier than today.',
                'error_btn_label': 'Go Back',
                'error_btn_url': '/helpdesks/create_ticket',
            })

        project = request.env['project.project'].sudo().browse(project_id).exists()
        vals = {
            'name': subject,
            'project_id': project.id,
            'partner_id': project.partner_id.id if project.partner_id else False,
            'deadline': ticket_deadline,
            'assign_date': post.get('assign_date') or date.today().isoformat(),
            'employee_ids': [(6, 0, employees.ids)],
            'assigned_user_ids': [(6, 0, assignee_ids)],
            'user_id': assignee_ids[0] if assignee_ids else False,
            'priority': post.get('priority') or default_priority,
        }
        integer_fields = ('team_id',)
        for field_name in integer_fields:
            value = post.get(field_name)
            if field_name in Ticket._fields and value and str(value).isdigit():
                vals[field_name] = int(value)

        if 'description' in Ticket._fields:
            vals['description'] = post.get('description') or ''

        # Some Helpdesk configurations require a team. Use the first available
        # team only when no team was explicitly submitted.
        if 'team_id' in Ticket._fields and not vals.get('team_id'):
            Team = request.env['helpdesk.team'].sudo()
            default_team = Team.search([], limit=1)
            if default_team:
                vals['team_id'] = default_team.id

        try:
            ticket = Ticket.create(vals)
        except Exception as error:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Ticket Creation Failed',
                'error_desc': str(error),
                'error_btn_label': 'Try Again',
                'error_btn_url': '/helpdesks/create_ticket',
            })

        return request.render('xsellence_portal.success_page', {
            'success_title': 'Ticket Created',
            'success_desc': 'Support ticket %s was created successfully.' % ticket.display_name,
            'success_btn_label': 'Back to Helpdesk',
            'success_btn_url': '/helpdesks',
        })
