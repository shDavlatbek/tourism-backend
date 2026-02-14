JAZZMIN_SETTINGS: dict = {
    'site_title': 'Villages Admin',
    'site_header': 'Villages',
    'site_brand': 'Villages',
    'welcome_sign': 'Turizm Qishloqlari',
    'copyright': 'Villages Project',
    'search_model': '',
    'topmenu_links': [],
    'usermenu_links': [{'model': 'auth.user'}],
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': [],
    'hide_models': [],

    'order_with_respect_to': [
        'auth', 'auth.user', 'auth.group',
        'main', 'main.city', 'main.village', 'main.gallery', 'main.comment', 'main.mainsettings',
    ],

    'icons': {
        # Apps
        'auth': 'fas fa-users-cog',
        'main': 'fas fa-mountain',

        # Auth models
        'auth.Group': 'fas fa-users',
        'auth.User': 'fas fa-user-tie',

        # Main app models
        'main.city': 'fas fa-city',
        'main.village': 'fas fa-home',
        'main.gallery': 'fas fa-images',
        'main.comment': 'fas fa-comments',
        'main.mainsettings': 'fas fa-cog',
    },

    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': False,
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {
        'auth.user': 'collapsible',
        'auth.group': 'vertical_tabs',
    },

    'language_chooser': True,
}
