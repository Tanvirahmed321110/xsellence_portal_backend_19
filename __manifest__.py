# -*- coding: utf-8 -*-
{
    "name": "Xsellence Portal",
    "version": "0.1",
    "summary": "Project, task, timesheet, employee, helpdes and support portal",
    "description": """
        Xsellence Portal provides a custom website dashboard for project,
        task, timesheet, employee, notification, and support workflows.
    """,
    "author": "Tanvir Ahmed,Shamiul Basir",
    "website": "https://www.xsellencebdltd.com",
    "license": "LGPL-3",
    "category": "Services/Xsellence Portal",
    "depends": [
        "base",
        "project",
        "hr",
        "hr_timesheet",
        "portal",
        "website",
        "product",
        "helpdesk",
    ],
    "data": [
        "security/security_group.xml",
        "security/ir.model.access.csv",
        "templates/layout.xml",
        "templates/dashboard.xml",
        "templates/projects.xml",
        "templates/project_details.xml",
        "templates/tasks.xml",
        "templates/timesheets.xml",
        "templates/helpdesk.xml",
        "templates/create_ticket.xml",
        "templates/add_task.xml",
        "templates/add_timesheet.xml",
        "templates/profile.xml",
        "templates/edit_profile.xml",
        "templates/create_project.xml",
        "templates/edit_project.xml",
        "templates/ticket_details.xml",
        "templates/task_details.xml",
        "templates/edit_task.xml",
        "templates/employees.xml",
        "templates/breadcrumb.xml",
        "templates/alert.xml",
        "templates/pagination.xml",

        #==========  Backend View  ==========
        "views/hr_announcement_views.xml",
        "views/project_inherit_view.xml",
        "views/project_task_inherit_view.xml",
        "views/helpdesk_inherit_view.xml",

        #==========  Backend Report  ==========
        "report/user_report_paperformat.xml",
        "report/user_report_templates.xml",
        "report/user_report_action.xml",
        'report/product_report_templates.xml',
    ],
    "assets": {
        "web.assets_backend": [
            # "xsellence_portal/static/src/css/custom_backend.css",
        ],
        "web.assets_frontend": [
            # "xsellence_portal/static/src/js/main.js",
            # "xsellence_portal/static/src/js/notice_board.js",
        ],
    },
    "demo": [
        "demo/demo.xml",
    ],
    "installable": True,
    "application": True,
}
