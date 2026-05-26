/**
 * ST CRM Helper — CRM Form Guard + Department Dropdown
 * ======================================================
 * Injected via doctype_js into all 6 CRM doctypes.
 *
 * 1. On form load — guards access by department (bypass for admin/manager)
 * 2. On new record — injects a department Link field dropdown filtered to
 *    the user's own departments (or all depts for admin/manager)
 */

(function () {
	"use strict";

	const GUARDED_DOCTYPES = [
		"CRM Lead",
		"CRM Deal",
		"CRM Organization",
		"CRM Task",
		"FCRM Note",
		"CRM Call Log",
	];

	GUARDED_DOCTYPES.forEach((dt) => {
		frappe.ui.form.on(dt, {
			async onload(frm) {
				// Ensure dept data is loaded
				const data = await stCrmHelper.fetchDeptData();

				// ── 1. Access guard ──────────────────────────────────────
				if (!frm.is_new()) {
					await _guardRecord(frm, data);
				}

				// ── 2. Department dropdown ───────────────────────────────
				await _setupDeptField(frm, data);
			},

			async refresh(frm) {
				// Re-setup dropdown on every refresh (handles new → saved transition)
				const data = await stCrmHelper.fetchDeptData();
				await _setupDeptField(frm, data);
			},
		});
	});


	// ── Access guard ──────────────────────────────────────────────────────────

	async function _guardRecord(frm, data) {
		try {
			// Bypass users (admin) and managers see everything
			if (data.bypass) return;

			const recordDept = frm.doc.department;

			// Legacy records with no department — allow through
			if (!recordDept) return;

			const allowed = data.departments || [];
			if (!allowed.includes(recordDept)) {
				frappe.set_route("List", frm.doctype);
				frappe.show_alert(
					{ message: __("Access restricted to your department."), indicator: "red" },
					4
				);
			}
		} catch (err) {
			console.error("ST CRM Helper: form guard error", err);
		}
	}


	// ── Department Link field setup ───────────────────────────────────────────

	async function _setupDeptField(frm, data) {
		try {
			// Fetch available dept options for this user
			const r = await frappe.call({
				method: "st_crm_helper.api.department.get_department_options",
				freeze: false,
			});

			const options = r.message || [];

			if (!options.length) return;

			// Set Link field filter so the picker only shows allowed depts
			frm.set_query("department", () => {
				return {
					filters: {
						name: ["in", options.map((o) => o.value)],
						is_active: 1,
					},
				};
			});

			// Auto-select dept on new records if user has exactly one dept
			if (frm.is_new() && !frm.doc.department && !data.bypass && options.length === 1) {
				frm.set_value("department", options[0].value);
			}

			// Make field visible and mandatory for non-admin users
			frm.set_df_property("department", "hidden", 0);
			frm.set_df_property("department", "reqd", data.bypass ? 0 : 1);

		} catch (err) {
			console.error("ST CRM Helper: dept field setup error", err);
		}
	}

})();
