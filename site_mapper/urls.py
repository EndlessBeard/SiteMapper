from django.urls import path
from . import views

app_name = 'site_mapper'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/start/', views.job_start, name='job_start'),
    path('jobs/<int:job_id>/next-depth/', views.job_process_next_depth, name='job_process_next_depth'),
    path('jobs/<int:job_id>/status/', views.job_status, name='job_status'),
    path('jobs/<int:job_id>/download/', views.job_download, name='job_download'),
    path('jobs/<int:job_id>/to-docx/', views.job_to_docx, name='job_to_docx'),
    path('jobs/<int:job_id>/stop/', views.job_stop, name='job_stop'),
    path('jobs/<int:job_id>/delete/', views.job_delete, name='job_delete'),
    path('api/jobs/<int:job_id>/status/', views.job_status_api, name='job_status_api'),
    path('filters/add/', views.add_filter, name='add_filter'),
    path('filters/delete/<int:filter_id>/', views.delete_filter, name='delete_filter'),
]