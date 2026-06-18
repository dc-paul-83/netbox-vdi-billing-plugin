from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label='VDI Billing',
    groups=(
        (
            'Reports',
            (
                PluginMenuItem(
                    link='plugins:netbox_vdi_billing:chargeback_overview',
                    link_text='Chargeback Overview',
                    permissions=['netbox_vdi_billing.view_vdiassignment'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_vdi_billing:vdiassignment_add',
                            title='Add Assignment',
                            icon_class='mdi mdi-plus-thick',
                            color='green',
                            permissions=['netbox_vdi_billing.add_vdiassignment'],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link='plugins:netbox_vdi_billing:vdiassignment_list',
                    link_text='All Assignments',
                    permissions=['netbox_vdi_billing.view_vdiassignment'],
                ),
            ),
        ),
        (
            'Configuration',
            (
                PluginMenuItem(
                    link='plugins:netbox_vdi_billing:vdibillingprofile_list',
                    link_text='Billing Profiles',
                    permissions=['netbox_vdi_billing.view_vdibillingprofile'],
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_vdi_billing:vdibillingprofile_add',
                            title='Add Profile',
                            icon_class='mdi mdi-plus-thick',
                            color='green',
                            permissions=['netbox_vdi_billing.add_vdibillingprofile'],
                        ),
                    ),
                ),
            ),
        ),
    ),
    icon_class='mdi mdi-currency-eur',
)
