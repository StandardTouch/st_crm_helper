import frappe


def after_install():
	"""Run once when app is installed on a site."""
	_create_default_department()
	_create_department_custom_fields()


def after_migrate():
	"""Run after every bench migrate — safe to run repeatedly."""
	_create_department_custom_fields()


def _create_default_department():
	if not frappe.db.exists("CRM Department", "General"):
		doc = frappe.new_doc("CRM Department")
		doc.department_name = "General"
		doc.is_active = 1
		doc.insert(ignore_permissions=True)
		frappe.db.commit()


def _create_department_custom_fields():
	"""
	Creates a 'department' Link field on all 6 CRM doctypes if it doesn't exist.
	Safe to run repeatedly — skips existing fields.
	"""
	DOCTYPES = [
		"CRM Lead",
		"CRM Deal",
		"CRM Organization",
		"CRM Task",
		"FCRM Note",
		"CRM Call Log",
	]

	INSERT_AFTER = {
		"CRM Lead":         "lead_owner",
		"CRM Deal":         "deal_owner",
		"CRM Organization": "website",
		"CRM Task":         "assigned_to",
		"FCRM Note":        "reference_doctype",
		"CRM Call Log":     "caller",
	}

	for dt in DOCTYPES:
		if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": "department"}):
			print(f"[ST CRM] 'department' already exists on {dt} — skipping")
			continue

		insert_after = INSERT_AFTER.get(dt, "")

		cf = frappe.new_doc("Custom Field")
		cf.update({
			"dt": dt,
			"module": "CRM Department",
			"label": "Department",
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "CRM Department",
			"insert_after": insert_after,
			"hidden": 0,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"search_index": 1,
			"reqd": 0,
			"translatable": 0,
		})
		cf.insert(ignore_permissions=True)
		print(f"[ST CRM] Created 'department' custom field on {dt} ✓")

	frappe.db.commit()
