import frappe

@frappe.whitelist()
def floor_extension(project, towers, floors, units=None):
    """
    Extend a project with towers/floors/units based on the Project Template.
    Only missing tasks are added.
    Hierarchy: Floor Planning (in project) -> Tower -> Floor -> Units
    """
    towers = [t.strip() for t in towers.split(",")]
    floors = int(floors)
    units = int(units) if units else None

    # Get project
    project_doc = frappe.get_doc("Project", project)

    # Get linked Project Template
    template_name = project_doc.project_template
    if not template_name:
        frappe.throw("Project does not have a Project Template assigned.")
    template = frappe.get_doc("Project Template", template_name)

    # Get Floor Planning task from the current project
    floor_plan_task = frappe.get_all(
        "Task",
        filters={"project": project, "subject": "Floor Planning"},
        fields=["name"]
    )
    if not floor_plan_task:
        frappe.throw("Current project does not have a 'Floor Planning' task.")
    floor_plan_task_name = floor_plan_task[0]["name"]

    # Build template pattern: Tower -> Floor -> Units
    template_pattern = {}
    for t in template.tasks:
        if t.subject.lower().startswith("tower"):
            tower_name = t.subject
            template_pattern[tower_name] = {}
            for f in template.tasks:
                if f.subject.startswith(f"{tower_name} - Floor") or f.subject.startswith(f"{tower_name} - F"):
                    floor_name = f.subject
                    units_list = [
                        u.subject
                        for u in template.tasks
                        if u.subject.startswith(f"{floor_name} - Unit")
                    ]
                    template_pattern[tower_name][floor_name] = units_list

    # Fetch existing tasks in project
    existing_tasks = frappe.get_all(
        "Task",
        filters={"project": project_doc.name},
        fields=["name", "subject", "parent_task"]
    )
    existing_subjects = {(t["subject"], t["parent_task"]): t for t in existing_tasks}

    # Helper to check if task exists by subject and parent
    def task_exists(subject, parent_name):
        key = (subject, parent_name)
        if key in existing_subjects:
            return frappe.get_doc("Task", existing_subjects[key]["name"])
        return None

    # Create towers/floors/units
    for tower in towers:
        tower_subject = f"Tower {tower}"
        tower_task = task_exists(tower_subject, parent_name=floor_plan_task_name)
        if not tower_task:
            tower_task = frappe.get_doc({
                "doctype": "Task",
                "project": project_doc.name,
                "subject": tower_subject,
                "is_group": 1,
                "parent_task": floor_plan_task_name
            })
            tower_task.insert()
            existing_subjects[(tower_subject, floor_plan_task_name)] = {"name": tower_task.name}

        # Determine existing floors under tower
        tower_floors = [
            t for t in existing_tasks
            if t.get("parent_task") == tower_task.name and "Floor" in t["subject"]
        ]
        existing_floor_numbers = []
        for f in tower_floors:
            try:
                num = int(f["subject"].split("Floor")[-1].strip())
                existing_floor_numbers.append(num)
            except:
                continue

        # Add missing floors
        for floor_num in range(floors):
            floor_subject = f"{tower_subject} - Floor {floor_num}"
            floor_task = task_exists(floor_subject, parent_name=tower_task.name)
            if not floor_task:
                floor_task = frappe.get_doc({
                    "doctype": "Task",
                    "project": project_doc.name,
                    "subject": floor_subject,
                    "is_group": 1,
                    "parent_task": tower_task.name
                })
                floor_task.insert()
                existing_subjects[(floor_subject, tower_task.name)] = {"name": floor_task.name}

            # Add units under this floor
            template_units = []
            if tower_subject in template_pattern:
                for f_name, u_list in template_pattern[tower_subject].items():
                    if f_name.endswith(str(floor_num)) or f_name.endswith(f"F{floor_num}"):
                        template_units = u_list
                        break

            # Override units if user gave a number
            if units:
                template_units = [f"{floor_subject} - Unit {i}" for i in range(units)]

            for unit in template_units:
                if not task_exists(unit, parent_name=floor_task.name):
                    unit_task = frappe.get_doc({
                        "doctype": "Task",
                        "project": project_doc.name,
                        "subject": unit,
                        "is_group": 0,
                        "parent_task": floor_task.name
                    })
                    unit_task.insert()
                    existing_subjects[(unit, floor_task.name)] = {"name": unit_task.name}

    frappe.db.commit()
    return "Towers, floors, and units added successfully!"
