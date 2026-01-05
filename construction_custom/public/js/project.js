frappe.ui.form.on("Project", {
    refresh(frm) {
        if (!frm.doc.__islocal) {

            frm.add_custom_button("Generate Towers/Floors", () => {

                let d = new frappe.ui.Dialog({
                    title: "Generate Towers, Floors & Units",
                    fields: [
                        {
                            label: "Towers (comma-separated)",
                            fieldname: "towers",
                            fieldtype: "Data",
                            reqd: 1
                        },
                        {
                            label: "No. of Floors",
                            fieldname: "floors",
                            fieldtype: "Int",
                            reqd: 1
                        },
                        {
                            label: "Units per Floor (optional)",
                            fieldname: "units",
                            fieldtype: "Int",
                            reqd: 0
                        }
                    ],
                    primary_action_label: "Generate",
                    primary_action(values) {

                        frappe.call({
                            method: "construction_custom.api.project.floor_extension",
                            args: {
                                project: frm.doc.name,
                                towers: values.towers,
                                floors: values.floors,
                                units: values.units
                            },
                            callback(r) {
                                if (!r.exc) {
                                    frappe.msgprint(r.message);
                                    frm.reload_doc();
                                }
                            }
                        });

                        d.hide();
                    }
                });

                d.show();
            });
        }
    }
});
