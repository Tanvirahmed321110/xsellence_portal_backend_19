from odoo import http
from odoo.http import request
from datetime import date, datetime
from odoo.tools import html2plaintext
from markupsafe import Markup, escape
from odoo.addons.xsellence_portal.utilitis.pagination import get_pager


class XsellencePortal(http.Controller):
    def _employee_query(self, employee_id):
        return f'?employee_id={employee_id}' if employee_id else ''
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

    def _can_manage_tasks(self):
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

    def _resolve_selected_employee(self, raw_employee_id):
        user = request.env.user
        current_employee = self._current_employee(user)
        selected_employee_id = int(raw_employee_id or 0)

        if not self._can_manage_tasks():
            return current_employee, current_employee.id if current_employee else 0

        if selected_employee_id:
            employee = request.env['hr.employee'].sudo().browse(selected_employee_id)
            if employee.exists():
                return employee, employee.id

        return current_employee, current_employee.id if current_employee else 0

    def _is_completed_stage(self, stage_name):
        normalized = (stage_name or '').strip().casefold()
        return any(keyword in normalized for keyword in ('done', 'complete', 'completed', 'closed', 'finish'))

    def _to_date(self, value):
        if isinstance(value, datetime):
            return value.date()
        return value

    def _is_task_overdue(self, task):
        deadline_date = self._to_date(task.date_deadline)
        return bool(deadline_date and deadline_date < date.today() and not self._is_completed_stage(task.stage_id.name))

    def _task_manager_only_response(self, back_url='/tasks'):
        return request.render('xsellence_portal.error_page', {
            'error_title': 'Access Denied',
            'error_desc': 'Only Project Manager users can create, edit, delete, or update tasks.',
            'error_btn_label': 'Back',
            'error_btn_url': back_url,
        })

    def _task_status_update_log_html(self, actor_name, old_stage_name, new_stage_name):
        actor = escape(actor_name or 'A user')
        old_stage = escape(old_stage_name or 'No Status')
        new_stage = escape(new_stage_name or 'No Status')
        return Markup(
            "<b>Task Status Changed</b><br/>%s changed task status from <b>%s</b> to <b>%s</b>."
        ) % (actor, old_stage, new_stage)

    def _dedupe_stage_records(self, stages):
        unique_stages = request.env['project.task.type'].sudo().browse()
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

    def _task_stage_model(self):
        return request.env['project.task.type'].sudo()

    def _get_task_stages(self, project_id=False):
        stages = self._task_stage_model().search([], order='sequence, id')
        return self._dedupe_stage_records(stages)

    def _resolve_task_stage_id(self, raw_stage_value, project_id=False):
        if not raw_stage_value:
            return False
        stage_value = str(raw_stage_value).strip()
        if not stage_value:
            return False
        if stage_value.isdigit():
            return int(stage_value)

        stages = self._get_task_stages(project_id=project_id)
        existing_stage = stages.filtered(lambda stage: (stage.name or '').strip().casefold() == stage_value.casefold())[:1]
        if existing_stage:
            return existing_stage.id

        create_vals = {'name': stage_value}
        if project_id:
            create_vals['project_ids'] = [(4, project_id)]
        return self._task_stage_model().create(create_vals).id

    def _get_visible_task_domain(self, user=None, selected_user=False):
        user = user or request.env.user
        domain = [('create_uid.login', '!=', '__system__')]

        target_user = selected_user or user
        if target_user:
            domain += ['|', ('user_ids', 'in', [target_user.id]), ('assigned_user_ids', 'in', [target_user.id])]

        return domain

    def _get_visible_task(self, task_id, user=None):
        domain = [('id', '=', task_id)] + self._get_visible_task_domain(user=user)
        return request.env['project.task'].sudo().search(domain, limit=1)

    # ========================
    # For ALl Tasks
    # ========================
    @http.route('/tasks', type='http', auth='user', website=True)
    def tasks_f(self, project_id=None, **kw):

        user = request.env.user
        status = kw.get('status')
        search = (kw.get('search') or '').strip()
        selected_employee, selected_employee_id = self._resolve_selected_employee(kw.get('employee_id'))
        selected_user = selected_employee.user_id if selected_employee and selected_employee.exists() and selected_employee.user_id else False

        domain = self._get_visible_task_domain(user=user, selected_user=selected_user)

        if project_id and str(project_id).isdigit():
            domain.append(('project_id', '=', int(project_id)))

        if status and str(status).isdigit():
            domain.append(('stage_id', '=', int(status)))
        if search:
            if search.isdigit():
                domain += ['|', ('name', 'ilike', search), ('id', '=', int(search))]
            else:
                domain.append(('name', 'ilike', search))

        # ===== Pagination Setup =====
        per_page = int(kw.get('per_page', 20))

        # main request
        Task = request.env['project.task'].sudo()
        total = Task.search_count(domain)

        pager = get_pager(
            url='/tasks',
            total=total,
            page=kw.get('page', 1),
            per_page=per_page,
            url_args={
                'search': search,
                'status': status or '',
                'employee_id': selected_employee_id or '',
                'project_id': int(project_id) if project_id and str(project_id).isdigit() else '',
            }
        )


        current_project_id = int(project_id) if project_id and str(project_id).isdigit() else False
        statuses = self._get_task_stages(project_id=current_project_id)

        tasks = Task.search(
            domain,
            order='create_date desc',
            offset=pager['offset'],
            limit=pager['per_page']
        )



        overdue_task_ids = {task.id for task in tasks if self._is_task_overdue(task)}

        return request.render('xsellence_portal.tasks_page', {
            'active_menu': 'tasks',
            'tasks': tasks,
            'overdue_task_ids': overdue_task_ids,
            'statuses': statuses,
            'task_stage_styles': {task.id: self._stage_badge_style(task.stage_id.name) for task in tasks},
            'can_manage_tasks': self._can_manage_tasks(),
            'search': search,
            'selected_status': status,
            'selected_employee_id': selected_employee_id,
            'pager': pager,
            'total': total,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard?employee_id=%s' % selected_employee_id if selected_employee_id else '/dashboard'},
                {'name': 'Tasks', 'url': False},
            ]
        })

    # ========================
    # For Task Details
    # ========================
    @http.route('/tasks/task_details/<int:task_id>', type='http', auth='user', website=True)
    def task_details_f(self, task_id, **kw):
        selected_employee_id = int(kw.get('employee_id') or 0)
        employee_query = self._employee_query(selected_employee_id)

        task = self._get_visible_task(task_id)
        if not task.exists():
            return request.redirect('/tasks')
        status_selection = self._get_task_stages(project_id=task.project_id.id if task.project_id else False)

        # log message
        messages = request.env['mail.message'].sudo().search([
            ('model', '=', 'project.task'),
            ('res_id', '=', task.id)
        ], order='date desc')

        return request.render('xsellence_portal.task_details_page', {
            'active_menu': 'tasks',
            'task': task,
            'selected_employee_id': selected_employee_id,
            'can_manage_tasks': self._can_manage_tasks(),
            'task_stage_style': self._stage_badge_style(task.stage_id.name),
            'status_selection': status_selection,
            'messages': messages,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': f'/dashboard{employee_query}' if employee_query else '/dashboard'},
                {'name': 'Tasks', 'url': f'/tasks{employee_query}' if employee_query else '/tasks'},
                {'name': 'Task Details', 'url': False},
            ]
        })

    # ========================
    # For Task Log Message Submit
    # ========================
    @http.route('/task/comment/<int:task_id>', type='http', auth='user', website=True, methods=['POST'],
                csrf=True)
    def project_comment(self, task_id, **post):
        selected_employee_id = int(post.get('employee_id') or 0)
        employee_query = self._employee_query(selected_employee_id)
        task = self._get_visible_task(task_id)

        if not task.exists():
            return request.redirect('/tasks')

        comment = post.get('comment')

        if comment:
            safe_comment = escape(comment)

            task.message_post(
                body=Markup("""
                           <b>Comment Added</b><br/>
                           %s
                       """) % safe_comment,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            # Notify other task members about the new comment in the same
            # sidebar/popup stream used for assignment updates.
            task.with_user(request.env.user)._create_comment_notifications(
                request.env.user.name,
                comment,
            )

        return request.redirect(f'/tasks/task_details/{task.id}{employee_query}')

    # ========================
    # For Task Update Status
    # ========================
    @http.route('/task/update_status', type='http', auth='user', methods=['POST'], csrf=True)
    def update_project_status(self, task_id=None, status=None, redirect_url=None, **kw):
        selected_employee_id = int(kw.get('employee_id') or 0)
        employee_query = self._employee_query(selected_employee_id)
        task = False
        if task_id:
            task = self._get_visible_task(int(task_id))
        if not task.exists():
            return request.redirect('/tasks')

        stage_id = self._resolve_task_stage_id(status, project_id=task.project_id.id if task else False)
        if task and stage_id and task.stage_id.id != stage_id:
            previous_stage_name = task.stage_id.name
            task.sudo().with_context(tracking_disable=True).write({'stage_id': stage_id})
            task.sudo().message_post(
                author_id=request.env.user.partner_id.id,
                body=self._task_status_update_log_html(
                    request.env.user.name,
                    previous_stage_name,
                    task.stage_id.name,
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        if not redirect_url:
            return request.redirect(f"/tasks/task_details/{task_id}{employee_query}")
        return request.redirect(f"/tasks")

    # ========================
    # For Add Task Route
    # ========================
    @http.route('/add_task', type='http', auth='user', website=True)
    def add_task_f(self, **kw):
        if not self._can_manage_tasks():
            return self._task_manager_only_response('/tasks')

        source = kw.get('source')
        selected_project_id = kw.get('project_id')

        if source == 'tasks':
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Tasks', 'url': '/tasks'},
                {'name': 'Add Task', 'url': False},
            ]
        elif source == 'projects':
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Projects', 'url': '/projects'},
                {'name': 'Add Task', 'url': False},
            ]
        else:
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Add Task', 'url': False},
            ]

        projects = request.env['project.project'].sudo().search([])
        users = request.env['res.users'].sudo().search([('login', '!=', '__system__')])
        current_project_id = int(selected_project_id) if selected_project_id and str(selected_project_id).isdigit() else False
        statuses = self._get_task_stages(project_id=current_project_id)
        priority = request.env['project.task'].sudo()._fields['custom_priority'].selection

        return request.render('xsellence_portal.add_task_page', {
            'active_menu': 'add_task',
            'breadcrumb': breadcrumb_data,
            'source': source,
            'projects': projects,
            'users': users,
            'statuses': statuses,
            'priority': priority,
            'today': date.today().strftime('%Y-%m-%d'),
            'selected_project_id': int(selected_project_id) if selected_project_id else False,
        })

    # ========================
    # For Task Submit Route
    # ========================
    @http.route('/add_task/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def add_task_submit(self, **kw):
        if not self._can_manage_tasks():
            return self._task_manager_only_response('/tasks')

        # Assignees (multiple select)
        assignee_ids = request.httprequest.form.getlist('user_ids')
        user_ids = [(6, 0, [int(uid) for uid in assignee_ids if uid])]

        task_name = (kw.get('name') or '').strip()
        if not task_name:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Creation Failed',
                'error_desc': 'Task name is required.',
                'error_btn_label': 'Try Again',
                'error_btn_url': '/add_task',
            })
        task_deadline = self._parse_portal_date(kw.get('date_deadline'))
        if task_deadline and task_deadline < date.today():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Creation Failed',
                'error_desc': 'Deadline cannot be earlier than today.',
                'error_btn_label': 'Try Again',
                'error_btn_url': '/add_task',
            })
        task = {
            'name': task_name,
            'project_id': int(kw.get('project_id')) if kw.get('project_id') else False,
            'date_assign': kw.get('date_assign') or date.today(),
            'date_deadline': kw.get('date_deadline'),
            'custom_priority': kw.get('custom_priority'),
            'user_ids': user_ids,
            'description': kw.get('description'),
        }
        stage_id = self._resolve_task_stage_id(
            kw.get('stage_id'),
            project_id=task['project_id'] if task.get('project_id') else False,
        )
        if stage_id:
            task['stage_id'] = stage_id

        new_task = request.env['project.task'].sudo().create(task)

        # ❌  Error Page
        if not new_task:
            return request.render('xsellence_portal.error_page', {
                'error_title': '❌ Task Creation Failed',
                'error_desc': 'Unable to create task.',
                'error_btn_label': 'Again Try',
                'error_btn_url': '/add_task',
            })

        # ✅ Success Page
        return request.render('xsellence_portal.success_page', {
            'success_title': 'Task Successfully Created',
            'success_desc': 'Your task has been added. You can now track it from the tasks list.',
            'success_btn_label': 'Show Tasks',
            'success_btn_url': '/tasks',
        })

    # ==========================
    # POST - Edit Page Form Page
    # ==========================
    @http.route('/task/edit/<int:task_id>', type='http', auth='user', website=True, methods=['GET'], csrf=True)
    def edit_task_form(self, task_id, **kw):
        if not self._can_manage_tasks():
            return self._task_manager_only_response(f"/tasks/task_details/{task_id}")

        task = self._get_visible_task(task_id)

        if not task.exists():
            return request.redirect('/tasks')

        projects = request.env['project.project'].sudo().search([])
        users = request.env['res.users'].sudo().search([('login', '!=', '__system__')])

        statuses = self._get_task_stages(project_id=task.project_id.id if task.project_id else False)
        priority = request.env['project.task'].sudo()._fields['custom_priority'].selection

        return request.render('xsellence_portal.edit_task_page', {
            'active_menu': 'tasks',
            'task': task,
            'task_description': html2plaintext(task.description or ''),
            'projects': projects,
            'users': users,
            'statuses': statuses,
            'priority': priority,
            'today': date.today().strftime('%Y-%m-%d'),
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Tasks', 'url': '/tasks'},
                {'name': 'Edit Task', 'url': False},
            ]
        })

    # ========================
    # POST - Edit Task Submit
    # ========================
    @http.route('/task/edit/<int:task_id>', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def edit_task_submit(self, task_id, **kw):
        if not self._can_manage_tasks():
            return self._task_manager_only_response(f"/tasks/task_details/{task_id}")

        task = self._get_visible_task(task_id)

        if not task.exists():
            return request.redirect('/tasks')

        assign_ids = request.httprequest.form.getlist('user_ids')
        user_ids = [(6, 0, [int(uid) for uid in assign_ids if uid])]
        task_name = (kw.get('name') or task.name or '').strip()
        if not task_name:
            return request.redirect(f"/task/edit/{task_id}")
        task_deadline = self._parse_portal_date(kw.get('date_deadline'))
        if task_deadline and task_deadline < date.today():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Update Failed',
                'error_desc': 'Deadline cannot be earlier than today.',
                'error_btn_label': 'Back to Edit Task',
                'error_btn_url': f'/task/edit/{task_id}',
            })

        vals = {
            'name': task_name,
            'project_id': int(kw['project_id']) if kw.get('project_id') else False,
            'date_deadline': kw.get('date_deadline') or False,
            'custom_priority': kw.get('custom_priority', ''),
            'description': kw.get('description', ''),
            'user_ids': user_ids,
        }
        stage_id = self._resolve_task_stage_id(
            kw.get('stage_id'),
            project_id=vals['project_id'] if vals.get('project_id') else (task.project_id.id if task.project_id else False),
        )
        if stage_id:
            vals['stage_id'] = stage_id

        task.write(vals)
        return request.redirect(f"/tasks/task_details/{task_id}")

    # ========================
    # For Delete Task
    # ========================
    @http.route('/task/delete', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def delete_task(self, task_id=None, **kw):
        if not self._can_manage_tasks():
            back_url = f"/tasks/task_details/{task_id}" if task_id and str(task_id).isdigit() else '/tasks'
            return self._task_manager_only_response(back_url)

        if not task_id:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Invalid Request',
                'error_desc': 'Task ID missing or invalid.',
                'error_btn_label': 'Show Tasks',
                'error_btn_url': '/tasks',
            })

        task = self._get_visible_task(int(task_id))
        if not task.exists():
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Not Found',
                'error_desc': 'This task is not available.',
                'error_btn_label': 'Show Tasks',
                'error_btn_url': '/tasks',
            })

        timesheets = request.env['account.analytic.line'].sudo().search([
            ('task_id', '=', task.id)
        ], limit=1)

        if timesheets:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Cannot Be Deleted',
                'error_desc': 'This task has timesheet entries. Please remove the timesheet entries first, then delete the task.',
                'error_btn_label': 'Back to Task',
                'error_btn_url': f'/tasks',
            })

        if task.exists():
            task.unlink()

        # ✅ Success Page
        return request.render('xsellence_portal.success_page', {
            'success_title': 'Task Successfully Deleted',
            'success_desc': 'Your task has been deleted successfully.',
            'success_btn_label': 'Show Tasks',
            'success_btn_url': '/tasks',
        })
