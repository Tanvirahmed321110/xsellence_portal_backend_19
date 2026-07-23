from calendar import month_abbr
from datetime import date, datetime, time, timedelta

from odoo import fields, http
from odoo.http import request


class XsellencePortal(http.Controller):
    def _safe_model(self, model_name):
        try:
            return request.env[model_name].sudo()
        except KeyError:
            return False

    def _format_hours(self, value, decimals=0):
        value = float(value or 0.0)
        if decimals:
            return f"{value:.{decimals}f}h"
        return f"{round(value)}h"

    def _format_percent(self, value):
        return max(0, min(100, int(round(value or 0))))

    def _format_time(self, value):
        if not value:
            return "--"
        localized = fields.Datetime.context_timestamp(request.env.user, value)
        return localized.strftime("%I:%M %p").lstrip("0")

    def _month_bounds(self, current_day):
        start_month = current_day.replace(day=1)
        if start_month.month == 12:
            next_month = start_month.replace(year=start_month.year + 1, month=1, day=1)
        else:
            next_month = start_month.replace(month=start_month.month + 1, day=1)
        return start_month, next_month

    def _count_weekdays(self, start_day, end_day):
        total = 0
        current = start_day
        while current <= end_day:
            if current.weekday() < 5:
                total += 1
            current += timedelta(days=1)
        return total

    def _resolve_selected_employee(self, active_employees, employee_param):
        current_user = request.env.user
        current_employee = request.env["hr.employee"].sudo().search(
            [("user_id", "=", current_user.id)],
            limit=1,
        )

        selected_employee = False
        if employee_param and str(employee_param).isdigit():
            candidate_id = int(employee_param)
            selected_employee = active_employees.filtered(lambda employee: employee.id == candidate_id)[:1]

        if not selected_employee and current_employee:
            selected_employee = active_employees.filtered(lambda employee: employee.id == current_employee.id)[:1]

        if not selected_employee and active_employees:
            selected_employee = active_employees[:1]

        return current_employee, selected_employee

    def _get_helpdesk_counts(self, selected_user):
        ticket_model = self._safe_model("helpdesk.ticket")
        if not ticket_model or not selected_user:
            return 0, 0

        base_domain = []
        if "user_id" in ticket_model._fields:
            base_domain = [("user_id", "=", selected_user.id)]
        elif "partner_id" in ticket_model._fields:
            base_domain = [("partner_id", "=", selected_user.partner_id.id)]

        if not base_domain or "stage_id" not in ticket_model._fields:
            return 0, 0

        helpdesk_new = ticket_model.search_count(base_domain + [("stage_id.name", "ilike", "new")])
        helpdesk_solved = ticket_model.search_count(
            base_domain + ["|", ("stage_id.name", "ilike", "solved"), ("stage_id.name", "ilike", "done")]
        )
        return helpdesk_new, helpdesk_solved

    def _get_leave_stats(self, selected_employee):
        leave_type_model = self._safe_model("hr.leave.type")
        leave_model = self._safe_model("hr.leave")
        allocation_model = self._safe_model("hr.leave.allocation")
        if not leave_type_model or not leave_model or not allocation_model or not selected_employee:
            return [
                {"label": "Sick Leave", "used": 0, "allocated": 0, "percent": 0},
                {"label": "Casual Leave", "used": 0, "allocated": 0, "percent": 0},
            ]

        def _days(record):
            return float(
                getattr(record, "number_of_days_display", False)
                or getattr(record, "number_of_days", False)
                or 0.0
            )

        stats = []
        for keyword, label in (("sick", "Sick Leave"), ("casual", "Casual Leave")):
            leave_type = leave_type_model.search([("name", "ilike", keyword)], limit=1)
            if not leave_type:
                stats.append({"label": label, "used": 0, "allocated": 0, "percent": 0})
                continue

            allocations = allocation_model.search(
                [
                    ("employee_id", "=", selected_employee.id),
                    ("holiday_status_id", "=", leave_type.id),
                    ("state", "=", "validate"),
                ]
            )
            leaves = leave_model.search(
                [
                    ("employee_id", "=", selected_employee.id),
                    ("holiday_status_id", "=", leave_type.id),
                    ("state", "=", "validate"),
                ]
            )

            allocated_days = sum(_days(allocation) for allocation in allocations)
            used_days = abs(sum(_days(leave) for leave in leaves))
            percent = (used_days / allocated_days * 100) if allocated_days else 0

            stats.append(
                {
                    "label": label,
                    "used": round(used_days, 1),
                    "allocated": round(allocated_days, 1),
                    "percent": self._format_percent(percent),
                }
            )

        return stats

    # ========================
    # For Dashboard Route
    # ========================
    @http.route("/dashboard", type="http", auth="user", website=True)
    def dashboard_f(self, **kw):
        user = request.env.user
        today = date.today()
        active_employees = request.env["hr.employee"].sudo().search(
            [("active", "=", True)],
            order="name asc",
        )

        current_employee, selected_employee = self._resolve_selected_employee(
            active_employees,
            kw.get("employee_id"),
        )
        selected_user = selected_employee.user_id if selected_employee and selected_employee.user_id else False

        is_admin = user.has_group("xsellence_portal.group_admin")
        is_project_manager = user.has_group("xsellence_portal.group_project_manager")
        is_general_employee = user.has_group("xsellence_portal.group_general_employee")
        is_portal = user.has_group("base.group_portal")
        is_internal = user.has_group("base.group_user")

        if is_admin:
            user_role = "admin"
        elif is_project_manager:
            user_role = "project_manager"
        elif is_general_employee:
            user_role = "general_employee"
        elif is_internal:
            user_role = "internal"
        elif is_portal:
            user_role = "portal"
        else:
            user_role = "public"

        if selected_user:
            task_domain = [
                ("create_uid.login", "!=", "__system__"),
                "|",
                ("user_ids", "in", [selected_user.id]),
                ("assigned_user_ids", "in", [selected_user.id]),
            ]
            project_domain = [
                ("active", "=", True),
                ("name", "!=", "Internal"),
                "|",
                ("user_id", "=", selected_user.id),
                ("assigned_user_ids", "in", [selected_user.id]),
            ]
        else:
            task_domain = [("id", "=", 0), ("create_uid.login", "!=", "__system__")]
            project_domain = [("id", "=", 0)]

        if selected_employee and selected_user:
            timesheet_domain = ["|", ("employee_id", "=", selected_employee.id), ("user_id", "=", selected_user.id)]
        elif selected_employee:
            timesheet_domain = [("employee_id", "=", selected_employee.id)]
        elif selected_user:
            timesheet_domain = [("user_id", "=", selected_user.id)]
        else:
            timesheet_domain = [("id", "=", 0)]

        Task = request.env["project.task"].sudo().with_context(active_test=False)
        Project = request.env["project.project"].sudo().with_context(active_test=False)
        Timesheet = request.env["account.analytic.line"].sudo()

        total_tasks = Task.search_count(task_domain)
        completed_tasks = Task.search_count(task_domain + [("custom_status", "=", "completed")])
        overdue_tasks = Task.search_count(
            task_domain + [("date_deadline", "<", today), ("custom_status", "not in", ["completed", "cancelled"])]
        )

        total_projects = Project.search_count(project_domain)
        completed_projects = Project.search_count(project_domain + [("custom_status", "=", "completed")])
        selected_projects = Project.search(project_domain, order="create_date desc", limit=5)

        filtered_timesheets = Timesheet.search(timesheet_domain)
        total_hours = sum(filtered_timesheets.mapped("unit_amount"))

        start_year = date(today.year, 1, 1)
        next_year = date(today.year + 1, 1, 1)
        yearly_timesheets = Timesheet.search(timesheet_domain + [("date", ">=", start_year), ("date", "<", next_year)])

        monthly_hours = {index: 0.0 for index in range(1, 13)}
        for timesheet in yearly_timesheets:
            if timesheet.date:
                monthly_hours[timesheet.date.month] += timesheet.unit_amount or 0.0

        highest_month_hours = max(monthly_hours.values()) if monthly_hours else 0.0
        attendance_chart = []
        for month_index in range(1, 13):
            hours = monthly_hours[month_index]
            percent = (hours / highest_month_hours * 100.0) if highest_month_hours else 0.0
            attendance_chart.append(
                {
                    "label": month_abbr[month_index],
                    "hours": self._format_hours(hours),
                    "percent": self._format_percent(percent),
                }
            )

        start_month, next_month = self._month_bounds(today)
        month_timesheets = Timesheet.search(
            timesheet_domain + [("date", ">=", start_month), ("date", "<", next_month)]
        )
        month_hours = sum(month_timesheets.mapped("unit_amount"))
        worked_days = len(set(month_timesheets.mapped("date")))
        workdays_so_far = max(1, self._count_weekdays(start_month, today))
        daily_average_hours = month_hours / worked_days if worked_days else 0.0
        attendance_ratio = worked_days / workdays_so_far * 100.0 if workdays_so_far else 0.0

        Attendance = self._safe_model("hr.attendance")
        check_in_text = "--"
        check_out_text = "--"
        today_duration_text = self._format_hours(daily_average_hours, 1)
        check_in_trend = "No data"
        check_out_trend = "No data"

        if Attendance and selected_employee:
            start_today = datetime.combine(today, time.min)
            end_today = datetime.combine(today + timedelta(days=1), time.min)
            today_attendances = Attendance.search(
                [
                    ("employee_id", "=", selected_employee.id),
                    ("check_in", ">=", start_today),
                    ("check_in", "<", end_today),
                ],
                order="check_in asc",
            )
            if today_attendances:
                check_in_text = self._format_time(today_attendances[0].check_in)
                check_in_trend = "Recorded today"
                checked_out = today_attendances.filtered(lambda attendance: attendance.check_out)
                if checked_out:
                    check_out_text = self._format_time(checked_out[-1].check_out)
                    today_hours = sum(checked_out.mapped("worked_hours"))
                    today_duration_text = self._format_hours(today_hours, 1)
                    check_out_trend = "Updated today"

        team_member_ids = set()
        for project in selected_projects:
            if project.user_id:
                team_member_ids.add(project.user_id.id)
            team_member_ids.update(project.assigned_user_ids.ids)

        project_progress = []
        status_class_map = {
            "planning": "tag-blue",
            "in_progress": "tag-green",
            "review": "tag-amber",
            "completed": "tag-purple",
            "cancelled": "tag-red",
        }
        status_label_map = dict(Project._fields["custom_status"].selection)
        for project in selected_projects:
            project_task_domain = [("project_id", "=", project.id)]
            project_task_total = Task.search_count(project_task_domain)
            project_task_done = Task.search_count(project_task_domain + [("custom_status", "=", "completed")])
            progress_percent = (
                self._format_percent(project_task_done / project_task_total * 100.0) if project_task_total else 0
            )
            project_progress.append(
                {
                    "name": project.name,
                    "percent": progress_percent,
                    "status_label": status_label_map.get(project.custom_status, "No Status"),
                    "status_class": status_class_map.get(project.custom_status, "tag-blue"),
                    "member_count": len(project.assigned_user_ids.ids),
                }
            )

        project_completion_pct = (
            self._format_percent(completed_projects / total_projects * 100.0) if total_projects else 0
        )
        task_completion_pct = self._format_percent(completed_tasks / total_tasks * 100.0) if total_tasks else 0
        on_time_pct = self._format_percent((total_tasks - overdue_tasks) / total_tasks * 100.0) if total_tasks else 0
        attendance_pct = self._format_percent(attendance_ratio)
        collaboration_pct = self._format_percent(len(team_member_ids) / max(1, len(selected_projects)) * 20.0)

        performance_metrics = [
            {"name": "Task Completion", "percent": task_completion_pct},
            {"name": "Project Completion", "percent": project_completion_pct},
            {"name": "On-time Delivery", "percent": on_time_pct},
            {"name": "Attendance", "percent": attendance_pct},
            {"name": "Collaboration", "percent": collaboration_pct},
        ]
        overall_score = self._format_percent(
            sum(metric["percent"] for metric in performance_metrics) / len(performance_metrics)
        )

        if overall_score >= 85:
            performance_label = "Excellent"
        elif overall_score >= 70:
            performance_label = "Good"
        elif overall_score >= 50:
            performance_label = "Average"
        else:
            performance_label = "Needs Work"

        average_time_per_task = (total_hours / total_tasks) if total_tasks else 0.0
        mini_cards = [
            {"label": "Avg. Time / Task", "value": self._format_hours(average_time_per_task, 1)},
            {"label": "Team Members", "value": str(len(team_member_ids))},
            {"label": "Performance Score", "value": f"{overall_score / 20:.1f}"},
            {"label": "Overdue Tasks", "value": str(overdue_tasks)},
        ]

        helpdesk_new, helpdesk_solved = self._get_helpdesk_counts(selected_user)
        leave_stats = self._get_leave_stats(selected_employee)

        dashboard_context = {
            "selected_employee": selected_employee,
            "selected_employee_id": selected_employee.id if selected_employee else False,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "helpdesk_new": helpdesk_new,
            "helpdesk_solved": helpdesk_solved,
            "attendance_chart": attendance_chart,
            "overall_score": overall_score,
            "performance_label": performance_label,
            "performance_metrics": performance_metrics,
            "project_progress": project_progress,
            "mini_cards": mini_cards,
            "working_hours_month": round(month_hours),
            "working_hours_month_label": start_month.strftime("%B"),
            "working_hours_daily_avg": self._format_hours(daily_average_hours, 1),
            "check_in_time": check_in_text,
            "check_in_expected": "09:00 AM",
            "check_in_trend": check_in_trend,
            "check_out_time": check_out_text,
            "check_out_duration": today_duration_text,
            "check_out_trend": check_out_trend,
            "leave_stats": leave_stats,
        }

        return request.render(
            "xsellence_portal.dashboard_page",
            {
                "active_menu": "dashboard",
                "user_type": user_role,
                "is_admin": is_admin,
                "is_project_manager": is_project_manager,
                "is_general_employee": is_general_employee,
                "current_employee": current_employee,
                "active_employees": active_employees,
                **dashboard_context,
            },
        )
