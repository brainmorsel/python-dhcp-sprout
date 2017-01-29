from . import views


def configure(add):
    add('GET',  '/', views.index)
    add('GET',  '/profile/', views.profile_list)
    add('*',    '/profile/new', views.profile_edit)
    add('*',    '/profile/{id}/edit', views.profile_edit)
    add('*',    '/profile/{id}/delete', views.profile_delete)
    add('GET',  '/staging/', views.staging_list)
    add('GET',  '/staging/{id}/assign-ip', views.staging_assign_ip)
    add('GET',  '/staging/{id}/delete', views.staging_delete)
    add('GET',  '/assigned/', views.assigned_list)
    add('GET',  '/assigned/{id}/delete', views.assigned_delete)
