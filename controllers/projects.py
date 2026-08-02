from odoo import http
from odoo.http import request
from datetime import date
from markupsafe import Markup, escape
from odoo.tools import html2plaintext
from odoo.addons.xsellence_portal.utilitis.pagination import get_pager


# ========== For Projects Page  ============
class XsellencePortal(http.Controller):
    def _stage_badge_style(self, stage_name):
        normalized = (stage_name or '').strip().casefold()
        keyword_palette = [
            (('done', 'complete', 'completed', 'closed', 'finish'), ('#166534', '#dcfce7', '#166534')),
            (('cancel', 'reject', 'blocked'), ('#991b1b', '#fee2e2', '#991b1b')),
            (('progress', 'working', 'active'), ('#1d4ed8', '#dbeafe', '#1d4ed8')),
            (('review', 'qa', 'test', 'approval'), ('#6d28d9', '#ede9fe', '#6d28d9')),
            (('new', 'todo', 'plan', 'inbox', 'today', 'week', 'month', 'later'), ('#9a3412', '#ffedd5', '#9a3412')),
        ]
        for keywords, colors in keyword_palette:
            if any(keyword in normalized for keyword in keywords):
                text_color, bg_color, border_color = colors
                return f"color:{text_color};background:{bg_color};border:1px solid {border_color};"

        fallback_palette = [
            ('#0f766e', '#ccfbf1', '#0f766e'),
            ('#1d4ed8', '#dbeafe', '#1d4ed8'),
            ('#7c2d12', '#ffedd5', '#7c2d12'),
            ('#6d28d9', '#ede9fe', '#6d28d9'),
            ('#be123c', '#ffe4e6', '#be123c'),
            ('#365314', '#ecfccb', '#365314'),
            ('#92400e', '#fef3c7', '#92400e'),
            ('#0f766e', '#cffafe', '#0f766e'),
        ]
        palette_index = sum(ord(char) for char in normalized) % len(fallback_palette) if normalized else 0
        text_color, bg_color, border_color = fallback_palette[palette_index]
        return f"color:{text_color};background:{bg_color};border:1px solid {border_color};"

    def _can_manage_projects(self):
        user = request.env.user
        return (
            user.has_group('xsellence_portal.group_project_manager')
            or user.has_group('xsellence_portal.group_admin')
        )

    def _project_manager_only_response(self, back_url='/projects'):
        return request.render('xsellence_portal.error_page', {
            'error_title': 'Access Denied',
            'error_desc': 'Only Project Manager users can create, edit, delete, or update projects.',
            'error_btn_label': 'Back',
            'error_btn_url': back_url,
        })

    def _dedupe_stage_records(self, stages):
        unique_stages = request.env['project.project.stage'].sudo().browse()
        seen_names = set()
        for stage in stages:
            key = (stage.name or '').strip().casefold()
            if not key or key in seen_names:
                continue
            seen_names.add(key)
            unique_stages |= stage
        return unique_stages

    def _parse_portal_date(self, raw_value):
        if not raw_value:
            return False
        try:
            return date.fromisoformat(str(raw_value).strip())
        except (TypeError, ValueError):
            return False

    def _project_stage_model(self):
        return request.env['project.project.stage'].sudo()

    def _get_project_stages(self):
        stages = self._project_stage_model().search([], order='sequence, id')
        return self._dedupe_stage_records(stages)

    def _resolve_project_stage_id(self, raw_stage_value):
        if not raw_stage_value:
            return False
        stage_value = str(raw_stage_value).strip()
        if not stage_value:
            return False
        if stage_value.isdigit():
            return int(stage_value)

        stages = self._get_project_stages()
        existing_stage = stages.filtered(lambda stage: (stage.name or '').strip().casefold() == stage_value.casefold())[:1]
        if existing_stage:
            return existing_stage.id

        return self._project_stage_model().create({'name': stage_value}).id

    # ========================
    # For All Projects
    # ========================
    @http.route('/projects', type='http', auth='user', website=True)
    def projects_f(self, **kw):
        selected_employee_id = int(kw.get('employee_id') or 0)
        search = (kw.get('search') or '').strip()
        selected_employee = request.env['hr.employee'].sudo().browse(selected_employee_id) if selected_employee_id else False
        selected_user = selected_employee.user_id if selected_employee and selected_employee.exists() and selected_employee.user_id else False

        base_domain = [
            ('active', '=', True),
            ('name', '!=', 'Internal')
        ]
        if selected_user:
            base_domain += ['|', ('user_id', '=', selected_user.id), ('assigned_user_ids', 'in', [selected_user.id])]

        # ===== Status Filter =====

        status_domain = []
        status = kw.get('status')
        if status and str(status).isdigit():
            status_domain = [('stage_id', '=', int(status))]

        # ===== Final Domain Merge =====
        domain = base_domain + status_domain
        if search:
            if search.isdigit():
                domain += ['|', ('name', 'ilike', search), ('id', '=', int(search))]
            else:
                domain.append(('name', 'ilike', search))

        Project = request.env['project.project'].sudo()
        total = Project.search_count(domain)

        # for pagination
        per_page = int(kw.get('per_page', 20))

        # ===== Pager Object Banano (reusable function call) =====
        pager = get_pager(
            url='/projects',
            total=total,
            page=kw.get('page', 1),
            per_page=per_page,
            url_args={
                'search': search,
                'status': status or '',
                'employee_id': selected_employee_id or '',
            }
        )

        projects = Project.search(
            domain,
            order='create_date desc',
            offset=pager['offset'],
            limit=pager['per_page']
        )

        statuses = self._get_project_stages()

        return request.render('xsellence_portal.projects_page', {
            'active_menu': 'projects',
            'projects': projects,
            'statuses': statuses,
            'project_stage_styles': {project.id: self._stage_badge_style(project.stage_id.name) for project in projects},
            'can_manage_projects': self._can_manage_projects(),
            'search': search,
            'status': status or '',
            'selected_employee_id': selected_employee_id,
            'pager': pager,
            'total': total,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard?employee_id=%s' % selected_employee_id if selected_employee_id else '/dashboard'},
                {'name': 'Projects', 'url': False},
            ]
        })

    # ========================
    # For Create Project
    # ========================
    @http.route('/create_project', type='http', auth='user', website=True)
    def create_project_f(self, **kw):
        if not self._can_manage_projects():
            return self._project_manager_only_response('/projects')

        source = kw.get('source')

        tags = request.env['project.tags'].sudo().search([])
        customers = request.env['res.partner'].sudo().search([])
        project_managers = request.env['res.users'].sudo().search([('share', '=', False)])
        users = request.env['res.users'].sudo().search([
            ('share', 'in', [True, False]),
            ('id', '!=', request.env.ref('base.user_admin').id)
        ])

        status_selection = self._get_project_stages()
        priority = request.env['project.project']._fields['custom_priority'].selection

        if source == 'projects':
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Projects', 'url': '/projects'},
                {'name': 'Create Project', 'url': False},
            ]
        else:
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Create Project', 'url': False},
            ]

        return request.render('xsellence_portal.create_project_page', {
            'active_menu': 'projects',
            'breadcrumb': breadcrumb_data,
            'project_managers': project_managers,
            'status_selection': status_selection,
            'users': users,
            'tags': tags,
            'customers': customers,
            'priority': priority,
            'today': date.today().strftime('%Y-%m-%d'),
        })

    # ========================
    # For Submit Project
    # ========================
    @http.route('/submit_project', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def submit_project(self, **post):
        if not self._can_manage_projects():
            return self._project_manager_only_response('/projects')

        assigned_user_ids = request.httprequest.form.getlist('assigned_user_ids')
        tags = request.httprequest.form.getlist('tag_ids')
        partner_id = post.get('partner_id')

        project_name = (post.get('name') or '').strip()
        if not project_name:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Project Creation Failed',
                'error_desc': 'Project name is required.',
                'error_btn_label': 'Try Again',
                'error_btn_url': '/create_project',
            })
        project_end_date = self._parse_portal_date(post.get('date'))
        if project_end_date and project_end_date < date.today():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Project Creation Failed',
                'error_desc': 'End date cannot be earlier than today.',
                'error_btn_label': 'Try Again',
                'error_btn_url': '/create_project',
            })
        create_data = {
            'name': project_name,
            'github_link': post.get('github_link'),
            'dev_link': post.get('dev_link'),
            'dev_password': post.get('dev_password'),
            'dev_user': post.get('dev_user'),
            'live_link': post.get('live_link'),
            'live_user': post.get('live_user'),
            'live_password': post.get('live_password'),
            'partner_id': int(partner_id) if partner_id else False,
            'user_id': int(post.get('user_id')) if post.get('user_id') else False,
            'date_start': post.get('date_start') or date.today(),
            'date': post.get('date') or date.today(),
            'custom_priority': post.get('custom_priority'),
            'description': post.get('description'),
            'assigned_user_ids': [(6, 0, [int(x) for x in assigned_user_ids if x])],
            'tag_ids': [(6, 0, [int(x) for x in tags if x])],
        }
        stage_id = self._resolve_project_stage_id(post.get('stage_id'))
        if stage_id:
            create_data['stage_id'] = stage_id

        project = request.env['project.project'].sudo().create(create_data)

        # ❌  Error Page
        if not project:
            return request.render('xsellence_portal.error_page', {
                'error_title': '❌ Project Creation Failed',
                'error_desc': 'Unable to create project.',
                'error_btn_label': 'Again Try',
                'error_btn_url': '/projects/create_project',
            })

        # ✅ Success Page
        return request.render('xsellence_portal.success_page', {
            'success_title': 'Project Successfully Created',
            'success_desc': 'Your project has been created successfully. You can now manage it and assign tasks to your team.',
            'success_btn_label': 'Show Projects',
            'success_btn_url': '/projects',
        })

    # ========================
    # For Project Details
    # ========================
    @http.route('/projects/details/<int:project_id>', type='http', auth='user', website=True)
    def project_details_f(self, project_id, **kw):

        request.session['last_project_id'] = project_id

        project = request.env['project.project'].sudo().browse(project_id)

        messages = request.env['mail.message'].sudo().search([
            ('model', '=', 'project.project'),
            ('res_id', '=', project.id)
        ], order='date desc')

        status_selection = self._get_project_stages()

        return request.render('xsellence_portal.project_details_page', {
            'active_menu': 'projects',
            'project': project,
            'can_manage_projects': self._can_manage_projects(),
            'project_stage_style': self._stage_badge_style(project.stage_id.name),
            'status_selection': status_selection,
            'messages': messages,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Projects', 'url': '/projects'},
                {'name': 'Project Details', 'url': False}
            ]
        })

    # ========================
    # Load message Submit
    # ========================
    @http.route('/project/comment/<int:project_id>', type='http', auth='user', website=True, methods=['POST'],
                csrf=True)
    def project_comment(self, project_id, **post):
        project = request.env['project.project'].sudo().browse(project_id)

        if not project.exists():
            return request.redirect('/projects')

        comment = post.get('comment')

        if comment:
            safe_comment = escape(comment)

            project.message_post(
                body=Markup("""
                        <b>Comment Added</b><br/>
                        %s
                    """) % safe_comment,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            # Notify other project members about the new comment in the same
            # sidebar/popup stream used for assignment updates.
            project.with_user(request.env.user)._create_comment_notifications(
                request.env.user.name,
                comment,
            )

        return request.redirect('/projects/details/%s' % project.id)


    # ========================
    # Project Status Update
    # ========================
    @http.route('/project/update_status', type='http', auth='user', csrf=True)
    def update_project_status(self, project_id=None, status=None, **kw):
        if not self._can_manage_projects():
            back_url = f"/projects/details/{project_id}" if project_id else '/projects'
            return self._project_manager_only_response(back_url)

        project = False
        if project_id:
            project = request.env['project.project'].sudo().browse(int(project_id))
        stage_id = self._resolve_project_stage_id(status)
        if project and stage_id:
            project.write({'stage_id': stage_id})

        return request.redirect(f"/projects/details/{project_id}")


    # ========================
    # GET - Edit Page Show
    # ========================
    @http.route('/project/edit/<int:project_id>', type='http', auth='user', website=True, methods=['GET'])
    def edit_project_page(self, project_id, **kwargs):
        if not self._can_manage_projects():
            return self._project_manager_only_response(f"/projects/details/{project_id}")

        # project fetch
        project = request.env['project.project'].sudo().browse(project_id)

        if not project.exists():
            return request.redirect('/projects')

        customers = request.env['res.partner'].sudo().search([])
        project_managers = request.env['res.users'].sudo().search([])
        users = request.env['res.users'].sudo().search([])
        tags = request.env['project.tags'].sudo().search([])

        status_field = request.env['project.project']._fields.get('stage_id')
        priority_field = request.env['project.project']._fields.get('custom_priority')
        status_selection = self._get_project_stages() if status_field else []
        priority_selection = priority_field.selection if priority_field else []

        # project object
        return request.render('xsellence_portal.edit_project_page', {
            'project': project,
            'project_desc': html2plaintext(project.description or ''),
            'customers': customers,
            'project_managers': project_managers,
            'users': users,
            'tags': tags,
            'status_selection': status_selection,
            'priority': priority_selection,
            'today': date.today().strftime('%Y-%m-%d'),
        })

    # ========================
    # POST - Edit Page Submit
    # ========================
    @http.route('/project/edit/<int:project_id>', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def edit_project_submit(self, project_id, **kw):
        if not self._can_manage_projects():
            return self._project_manager_only_response(f"/projects/details/{project_id}")

        project = request.env['project.project'].sudo().browse(project_id)

        if not project.exists():
            return request.redirect('/projects')

        def safe_int(value):
            return int(value) if value and str(value).isdigit() else False

        tag_ids = request.httprequest.form.getlist('tag_ids')
        tag_ids = [safe_int(item) for item in tag_ids if safe_int(item)]

        assigned_user_ids = request.httprequest.form.getlist('assigned_user_ids')
        assigned_user_ids = [safe_int(user) for user in assigned_user_ids if safe_int(user)]
        project_name = (kw.get('name') or project.name or '').strip()
        if not project_name:
            return request.redirect(f"/project/edit/{project_id}")
        project_end_date = self._parse_portal_date(kw.get('date'))
        if project_end_date and project_end_date < date.today():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Project Update Failed',
                'error_desc': 'End date cannot be earlier than today.',
                'error_btn_label': 'Back to Edit Project',
                'error_btn_url': f'/project/edit/{project_id}',
            })

        vals = {
            'name': project_name,
            'partner_id': safe_int(kw.get('partner_id')),
            'user_id': safe_int(kw.get('user_id')),
            'date_start': kw.get('date_start') or False,
            'date': kw.get('date') or False,
            'description': kw.get('description', ''),
            'custom_priority': kw.get('custom_priority', ''),
            'tag_ids': [(6, 0, tag_ids)],
            'assigned_user_ids': [(6, 0, assigned_user_ids)],

            # ===== Team Leader Fields  =====
            'github_link': kw.get('github_link', ''),
            'live_link': kw.get('live_link', ''),
            'live_user': kw.get('live_user', ''),
            'live_password': kw.get('live_password', ''),
            'dev_link': kw.get('dev_link', ''),
            'dev_user': kw.get('dev_user', ''),
            'dev_password': kw.get('dev_password', ''),
        }
        stage_id = self._resolve_project_stage_id(kw.get('stage_id'))
        if stage_id:
            vals['stage_id'] = stage_id

        project.write(vals)
        return request.redirect(f"/projects/details/{project_id}")

    # ========================
    # POST - Project Delete
    # ========================
    @http.route('/project/delete', type="http", auth="user", methods=['POST'], website=True, csrf=True)
    def delete_project(self, project_id=None, **kw):
        if not self._can_manage_projects():
            back_url = f"/projects/details/{project_id}" if project_id and str(project_id).isdigit() else '/projects'
            return self._project_manager_only_response(back_url)

        last_id = request.session.get('last_project_id')

        # 1. Validate project_id first
        if not project_id or not str(project_id).isdigit():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Invalid Request',
                'error_desc': 'Project ID missing or invalid.',
                'error_btn_label': 'Retry',
                'error_btn_url': f'/projects/details/{last_id}' if last_id else '/projects',
            })

        project = request.env['project.project'].sudo().browse(int(project_id))

        # 3. Get project tasks
        tasks = request.env['project.task'].sudo().with_context(active_test=False).search([
            ('project_id', '=', project.id)
        ])

        # 4. Check timesheet entries under this project/task
        timesheet_domain = [('project_id', '=', project.id)]

        if tasks:
            timesheet_domain = [
                '|',
                ('project_id', '=', project.id),
                ('task_id', 'in', tasks.ids),
            ]

        timesheet = request.env['account.analytic.line'].sudo().search(
            timesheet_domain,
            limit=1
        )

        # 5. If task + timesheet exists, do not delete
        if tasks and timesheet:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Project Cannot Be Deleted',
                'error_desc': 'This project has tasks with timesheet entries. Please remove the timesheet entries first, or archive the project instead of deleting it.',
                'error_btn_label': 'Back to Project',
                'error_btn_url': f'/projects/details/{project.id}',
            })

        # 6. Safe delete if no task timesheet exists
        project.unlink()

        return request.render('xsellence_portal.success_page', {
            'success_title': 'Project Deleted Successfully',
            'success_desc': 'The project has been permanently deleted and is no longer available.',
            'success_btn_label': 'Show All Projects',
            'success_btn_url': '/projects',
        })
