from odoo import http
from odoo.http import request
from datetime import date
from odoo.tools import html2plaintext
from markupsafe import Markup, escape
from odoo.addons.xsellence_portal.utilitis.pagination import get_pager


class XsellencePortal(http.Controller):
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

    def _task_stage_model(self):
        return request.env['project.task.type'].sudo()

    def _get_task_stages(self, project_id=False):
        domain = [('user_id', '=', False)]
        if project_id:
            domain += ['|', ('project_ids', '=', False), ('project_ids', 'in', [project_id])]
        stages = self._task_stage_model().search(domain, order='sequence, id')
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
        selected_employee_id = int(kw.get('employee_id') or 0)
        selected_employee = request.env['hr.employee'].sudo().browse(selected_employee_id) if selected_employee_id else False
        selected_user = selected_employee.user_id if selected_employee and selected_employee.exists() and selected_employee.user_id else False

        domain = self._get_visible_task_domain(user=user, selected_user=selected_user)

        if project_id and str(project_id).isdigit():
            domain.append(('project_id', '=', int(project_id)))

        if status and str(status).isdigit():
            domain.append(('stage_id', '=', int(status)))

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



        return request.render('xsellence_portal.tasks_page', {
            'active_menu': 'tasks',
            'tasks': tasks,
            'statuses': statuses,
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
            'status_selection': status_selection,
            'messages': messages,
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Tasks', 'url': '/tasks'},
                {'name': 'Task Details', 'url': False},
            ]
        })

    # ========================
    # For Task Log Message Submit
    # ========================
    @http.route('/task/comment/<int:task_id>', type='http', auth='user', website=True, methods=['POST'],
                csrf=True)
    def project_comment(self, task_id, **post):
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

        return request.redirect('/tasks/task_details/%s' % task.id)

    # ========================
    # For Task Update Status
    # ========================
    @http.route('/task/update_status', type='http', auth='user', methods=['POST'], csrf=True)
    def update_project_status(self, task_id=None, status=None, redirect_url=None, **kw):
        task = False
        if task_id:
            task = self._get_visible_task(int(task_id))
        stage_id = self._resolve_task_stage_id(status, project_id=task.project_id.id if task else False)
        if task and stage_id:
            task.write({'stage_id': stage_id})

        if not redirect_url:
            return request.redirect(f"/tasks/task_details/{task_id}")
        return request.redirect(f"/tasks")

    # ========================
    # For Add Task Route
    # ========================
    @http.route('/add_task', type='http', auth='user', website=True)
    def add_task_f(self, **kw):
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
        task = self._get_visible_task(task_id)

        if not task.exists():
            return request.redirect('/tasks')

        assign_ids = request.httprequest.form.getlist('user_ids')
        user_ids = [(6, 0, [int(uid) for uid in assign_ids if uid])]
        task_name = (kw.get('name') or task.name or '').strip()
        if not task_name:
            return request.redirect(f"/task/edit/{task_id}")

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
