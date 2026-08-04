import re
from odoo import http
from odoo.http import request
from datetime import date
from odoo.addons.xsellence_portal.utilitis.pagination import get_pager


class XsellencePortal(http.Controller):
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

    def _get_visible_task_domain(self):
        return [('create_uid.login', '!=', '__system__')]

    def _get_visible_projects(self):
        return request.env['project.project'].sudo().search([])

    def _get_visible_tasks(self, project_id=False):
        domain = list(self._get_visible_task_domain())
        if project_id:
            domain.append(('project_id', '=', project_id))
        return request.env['project.task'].sudo().search(domain)

    def _get_visible_task(self, task_id):
        return request.env['project.task'].sudo().search(
            [('id', '=', task_id)] + self._get_visible_task_domain(),
            limit=1,
        )

    def _convert_time_input_to_float(self, time_value):

        time_value = str(time_value or "0").strip()

        # Allow: 1, 1.7, 1.07, 1.22, 1.59
        if not re.match(r"^\d+(\.(\d|[0-5]\d))?$", time_value):
            raise ValueError("Invalid time format")

        if "." not in time_value:
            return float(time_value)

        hour_part, minute_part = time_value.split(".")

        hours = int(hour_part)
        minutes = int(minute_part)

        if minutes >= 60:
            raise ValueError("Minutes must be less than 60")

        return hours + (minutes / 60.0)

    # ========================
    # For All Timesheets
    # ========================
    @http.route('/timesheets', type='http', auth='user', website=True)
    def timesheet_f(self, **kw):
        user = request.env.user

        today = date.today().strftime('%Y-%m-%d')

        selected_employee, selected_employee_id = self._resolve_selected_employee(kw.get('employee_id'))
        selected_project_id = int(kw.get('project_id') or 0)
        selected_start_date = kw.get('start_date', '')
        selected_end_date = kw.get('end_date', '')

        selected_user = selected_employee.user_id if selected_employee and selected_employee.exists() and selected_employee.user_id else False
        selected_employee_scope = self._selected_employee_scope(selected_employee)

        if selected_employee_scope and selected_user:
            base_domain = ['|', ('user_id', '=', selected_user.id), ('employee_id', 'in', selected_employee_scope.ids)]
        elif selected_employee_scope:
            base_domain = [('employee_id', 'in', selected_employee_scope.ids)]
        else:
            employees = request.env['hr.employee'].sudo().search([
                ('user_id', '=', user.id)
            ])
            base_domain = [
                '|',
                ('user_id', '=', user.id),
                ('employee_id', 'in', employees.ids),
            ]

        # Fast Project Dropdown using read_group
        project_groups = request.env['account.analytic.line'].sudo().read_group(
            domain=base_domain + [('project_id', '!=', False)],
            fields=['project_id'],
            groupby=['project_id'],
            lazy=False,
        )

        project_ids = [
            group['project_id'][0]
            for group in project_groups
            if group.get('project_id')
        ]

        project_filter_options = request.env['project.project'].sudo().browse(project_ids).sorted(
            lambda p: p.name or ''
        )

        # Final table domain
        domain = list(base_domain)

        if selected_project_id:
            domain.append(('project_id', '=', selected_project_id))

        if selected_start_date:
            domain.append(('date', '>=', selected_start_date))

        if selected_end_date:
            domain.append(('date', '<=', selected_end_date))



        # for pagination
        per_page = int(kw.get('per_page', 24))
        total = request.env['account.analytic.line'].sudo().search_count(domain)

        # ===== Pager Object Banano (reusable function call) =====
        pager = get_pager(
            url='/timesheets',
            total=total,
            page=kw.get('page', 1),
            per_page=per_page,
            url_args={
                'employee_id': selected_employee_id if selected_employee_id else '',
                'project_id': selected_project_id if selected_project_id else '',
                'start_date': selected_start_date,
                'end_date': selected_end_date,
            }
        )

        timesheets = request.env['account.analytic.line'].sudo().search(
            domain,
            order='date desc, id desc',
            offset=pager['offset'],
            limit=pager['per_page']
        )

        return request.render('xsellence_portal.timesheet_page', {
            'active_menu': 'timesheets',
            'timesheets': timesheets,
            'pager': pager,
            'total': total,

            'project_filter_options': project_filter_options,
            'selected_project_id': selected_project_id,
            'selected_employee_id': selected_employee_id,

            'selected_start_date': selected_start_date or '',
            'selected_end_date': selected_end_date or '',

            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard?employee_id=%s' % selected_employee_id if selected_employee_id else '/dashboard'},
                {'name': 'Timesheets', 'url': False},
            ]
        })


    # ========================
    # For Add  Timesheet
    # ========================
    @http.route('/add_timesheet', type='http', auth='user', website=True)
    def add_timesheet_f(self, **kw):
        source = kw.get('source')
        today = date.today()
        selected_project_id = int(kw.get('project_id') or 0)
        selected_task_id = int(kw.get('task_id') or 0)

        projects = self._get_visible_projects()
        selected_project = projects.filtered(lambda project: project.id == selected_project_id)[:1]
        tasks = self._get_visible_tasks(selected_project.id if selected_project else False)
        selected_task = tasks.filtered(lambda task: task.id == selected_task_id)[:1]

        if source == 'timesheets':
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Timesheets', 'url': '/timesheets'},
                {'name': 'Add Timesheet', 'url': False},
            ]

        else:
            breadcrumb_data = [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Timesheets', 'url': False},
            ]

        return request.render('xsellence_portal.add_timesheet_page', {
            'active_menu': 'add_timesheet',
            'breadcrumb': breadcrumb_data,
            'today': today,
            'projects': projects,
            'tasks': tasks,
            'selected_project': selected_project,
            'selected_task': selected_task,
        })

    # ========================
    # For Task  Timesheet
    # ========================
    @http.route('/tasks/add_timesheet', type='http', auth='user', website=True)
    def add_timesheet_from_task(self, **kw):
        task_id = int(kw.get('task_id', 0))
        project_id = int(kw.get('project_id', 0))

        selected_task = self._get_visible_task(task_id)
        selected_project = request.env['project.project'].sudo().browse(project_id).exists()
        if task_id and not selected_task:
            return request.redirect('/tasks')
        if selected_task and selected_task.project_id:
            selected_project = selected_task.project_id

        projects = self._get_visible_projects()
        tasks = self._get_visible_tasks(selected_project.id if selected_project else False)

        return request.render('xsellence_portal.add_timesheet_page', {
            'active_menu': 'add_timesheet',
            'selected_task': selected_task,
            'tasks': tasks,
            'projects': projects,
            'today': date.today(),
            'selected_project': selected_project,  # ✅ fixed
            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Tasks', 'url': '/tasks'},
                {'name': 'Add Timesheet', 'url': False},
            ]
        })

    # ========================
    # For Submit Timesheet
    # ========================
    @http.route('/tasks/add_timesheet/submit', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def add_timesheet_from_submit(self, **kw):
        task_id = int(kw.get('task_id', 0))
        project_id = int(kw.get('project_id', 0))

        try:
            unit_amount = self._convert_time_input_to_float(kw.get('unit_amount'))
        except ValueError:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Invalid Time Spent',
                'error_desc': 'Please enter valid time. Example: 1.5 = 1 hour 30 minutes, 1.22 = 1 hour 22 minutes.',
                'error_btn_label': 'Go Back',
                'error_btn_url': f'/tasks/add_timesheet?task_id={task_id}&project_id={project_id}',
            })

        task = self._get_visible_task(task_id)
        if task_id and not task:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Not Found',
                'error_desc': 'This task is not available for timesheet entry.',
                'error_btn_label': 'Show Tasks',
                'error_btn_url': '/tasks',
            })
        if not project_id:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Project Required',
                'error_desc': 'Please select a project before submitting the timesheet.',
                'error_btn_label': 'Go Back',
                'error_btn_url': f'/tasks/add_timesheet?task_id={task_id}&project_id={project_id}',
            })
        if not task_id:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Required',
                'error_desc': 'Please select a task before submitting the timesheet.',
                'error_btn_label': 'Go Back',
                'error_btn_url': f'/tasks/add_timesheet?task_id={task_id}&project_id={project_id}',
            })
        if task.project_id.id != project_id:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Task Mismatch',
                'error_desc': 'The selected task does not belong to the selected project.',
                'error_btn_label': 'Go Back',
                'error_btn_url': f'/tasks/add_timesheet?task_id={task_id}&project_id={project_id}',
            })

        date_str = kw.get('date')
        description = kw.get('name', '')

        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

        # ❌ Employee
        if not employee:
            return request.render('xsellence_portal.error_page', {
                'error_title': 'Employee Not Found',
                'error_desc': 'No employee record linked to your account. Please contact admin.',
                'error_btn_label': 'Go Back',
                'error_btn_url': f'/tasks/add_timesheet?task_id={task_id}&project_id={project_id}',
            })

        vals = {
            'task_id': task_id,
            'project_id': project_id,
            'employee_id': employee.id,
            'date': date_str,
            'name': description,
            'unit_amount': unit_amount,
        }

        timesheet = request.env['account.analytic.line'].sudo().create(vals)

        # ❌ Error
        if not timesheet:
            return request.render('xsellence_portal.error_page', {
                'error_title': '❌ Timesheet Creation Failed',
                'error_desc': 'Unable to save timesheet entry.',
                'error_btn_label': 'Try Again',
                'error_btn_url': f'/tasks/add_timesheet?task_id={task_id}&project_id={project_id}',
            })

        # ✅ Success
        return request.render('xsellence_portal.success_page', {
            'success_title': '✔️ Timesheet Submitted',
            'success_desc': 'Your timesheet entry has been saved successfully.',
            'success_btn_label': 'View Timesheets',
            'success_btn_url': '/timesheets',
        })

    # ========================
    # For Delete Timesheet
    # ========================
    @http.route('/timesheets/delete', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def delete_timesheet_f(self, **post):
        user = request.env.user
        timesheet_id = int(post.get('timesheet_id') or 0)

        employees = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ])

        timesheet = request.env['account.analytic.line'].sudo().search([
            ('id', '=', timesheet_id),
            '|',
            ('user_id', '=', user.id),
            ('employee_id', 'in', employees.ids),
        ], limit=1)

        if not timesheet:
            return request.render('xsellence_portal.error_page', {
                'error_title': '❌ Delete Failed',
                'error_desc': 'Timesheet not found or you are not allowed to delete it.',
                'error_btn_label': 'View Timesheets',
                'error_btn_url': '/timesheets',
            })

        timesheet.unlink()

        return request.render('xsellence_portal.success_page', {
            'success_title': '✔️ Timesheet Deleted',
            'success_desc': 'Your timesheet entry has been deleted successfully.',
            'success_btn_label': 'View Timesheets',
            'success_btn_url': '/timesheets',
        })
