from odoo import http
from odoo.http import request


class XsellencePortalHelpdesk(http.Controller):

    @staticmethod
    def _safe_model(model_name):
        try:
            return request.env[model_name].sudo()
        except KeyError:
            return False

    @staticmethod
    def _selection_values(model, field_name):
        field = model._fields.get(field_name)
        if not field or not field.selection:
            return []
        selection = field.selection
        if isinstance(selection, str):
            return getattr(model, selection)()
        return selection(model) if callable(selection) else selection

    # ========================
    # Helpdesk page
    # ========================
    @http.route('/helpdesks', type='http', auth='user', website=True)
    def helpdesk_f(self, **kw):
        user = request.env.user

        tickets = request.env['helpdesk.ticket'].sudo().search([
            ('user_id', '=', user.id)
        ])

        tickets_new = tickets.filtered(lambda ticket: ticket.stage_id.name == 'New')
        tickets_in_progress = tickets.filtered(lambda ticket: ticket.stage_id.name == 'In Progress')
        tickets_solved = tickets.filtered(lambda t: t.stage_id.name == 'Solved')
        tickets_cancelled = tickets.filtered(lambda t: t.stage_id.name == 'Cancelled')

        return request.render('xsellence_portal.helpdesk_page', {
            'active_menu': 'helpdesk',
            'tickets': tickets,  # All tickets (in case you need them all in the loop)
            'tickets_new': tickets_new,
            'tickets_in_progress': tickets_in_progress,
            'tickets_solved': tickets_solved,
            'tickets_cancelled': tickets_cancelled,

            'count_new': len(tickets_new),
            'count_in_progress': len(tickets_in_progress),
            'count_solved': len(tickets_solved),
            'count_cancelled': len(tickets_cancelled),
        })

    # ========================
    # Helpdesk ticket details
    # ========================
    @http.route('/helpdesks/ticket_details/<int:ticket_id>', type='http', auth='user', website=True)
    def ticket_details_f(self, ticket_id,**kw):
        
        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            return request.redirect('/helpdesks')


        return request.render('xsellence_portal.ticket_details_page', {
            'active_menu': 'helpdesk',
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Helpdesk', 'url': '/helpdesk'},
                {'name': 'Ticket Details', 'url': False},
            ],
        })

    # ========================
    # Create ticket page
    # ========================
    @http.route('/helpdesk/create_ticket', type='http', auth='user', website=True, methods=['GET'])
    def create_ticket_page(self, **kw):
        Ticket = self._safe_model('helpdesk.ticket')
        if not Ticket:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Helpdesk App Not Installed',
                'error_desc': 'Install the Odoo Helpdesk app to create support tickets from this portal.',
                'error_btn_label': 'Back to Helpdesk',
                'error_btn_url': '/helpdesk',
            })

        Team = self._safe_model('helpdesk.team')
        teams = Team.search([], order='name asc') if Team else request.env['res.users'].browse()

        return request.render('xsellence_portal.create_ticket_page', {
            'active_menu': 'helpdesk',
            'customers': request.env['res.partner'].sudo().search(
                [('active', '=', True)],
                order='name asc',
                limit=500,
            ),
            'users': request.env['res.users'].sudo().search(
                [('active', '=', True), ('share', '=', False)],
                order='name asc',
            ),
            'teams': teams,
            'projects': request.env['project.project'].sudo().search(
                [('active', '=', True)],
                order='name asc',
            ),
            'priorities': self._selection_values(Ticket, 'priority'),
            'has_project_field': 'project_id' in Ticket._fields,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Helpdesk', 'url': '/helpdesk'},
                {'name': 'Create Ticket', 'url': False},
            ],
        })

    # ========================
    # Submit ticket
    # ========================
    @http.route(
        '/helpdesk/create_ticket/submit',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def submit_ticket(self, **post):
        Ticket = self._safe_model('helpdesk.ticket')
        if not Ticket:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Helpdesk App Not Installed',
                'error_desc': 'The support ticket could not be created because the Odoo Helpdesk app is unavailable.',
                'error_btn_label': 'Back to Helpdesk',
                'error_btn_url': '/helpdesk',
            })

        subject = (post.get('name') or '').strip()
        if not subject:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Ticket Subject Required',
                'error_desc': 'Enter a subject before submitting the support ticket.',
                'error_btn_label': 'Go Back',
                'error_btn_url': '/helpdesk/create_ticket',
            })

        vals = {'name': subject}
        integer_fields = ('partner_id', 'user_id', 'team_id', 'project_id')
        for field_name in integer_fields:
            value = post.get(field_name)
            if field_name in Ticket._fields and value and str(value).isdigit():
                vals[field_name] = int(value)

        if 'description' in Ticket._fields:
            vals['description'] = post.get('description') or ''

        priority = post.get('priority')
        if 'priority' in Ticket._fields and priority:
            vals['priority'] = priority

        # Some Helpdesk configurations require a team. Use the first available
        # team only when no team was explicitly submitted.
        if 'team_id' in Ticket._fields and not vals.get('team_id'):
            Team = self._safe_model('helpdesk.team')
            default_team = Team.search([], limit=1) if Team else False
            if default_team:
                vals['team_id'] = default_team.id

        try:
            ticket = Ticket.create(vals)
        except Exception as error:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Ticket Creation Failed',
                'error_desc': str(error),
                'error_btn_label': 'Try Again',
                'error_btn_url': '/helpdesk/create_ticket',
            })

        return request.render('xsellence_portal.success_page', {
            'success_title': 'Ticket Created',
            'success_desc': 'Support ticket %s was created successfully.' % ticket.display_name,
            'success_btn_label': 'Back to Helpdesk',
            'success_btn_url': '/helpdesk',
        })
