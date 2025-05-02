from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse

from .models import Link, SiteMapJob
from .core.site_processor import start_job_processing

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'type', 'depth', 'processed', 'starting_url')
    list_filter = ('type', 'processed', 'depth')
    search_fields = ('url', 'starting_url')

@admin.register(SiteMapJob)
class SiteMapJobAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'total_links', 'processed_links', 'max_depth', 'current_depth', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'start_urls')
    readonly_fields = ('created_at', 'updated_at', 'total_links', 'processed_links')
    
    def progress(self, obj):
        if obj.total_links == 0:
            percentage = 0
        else:
            percentage = int((obj.processed_links / obj.total_links) * 100) if obj.total_links > 0 else 0
        
        return format_html(
            '<div style="width:100px; background-color:#f8f9fa; height:20px; border:1px solid #dee2e6;">'
            '<div style="width:{}%; background-color:#007bff; height:100%;"></div>'
            '</div> {}%',
            percentage, percentage
        )
    
    progress.short_description = 'Progress'
    
    def action_buttons(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="{}">Start</a>',
                reverse('admin:start_job', args=[obj.pk])
            )
        elif obj.status == 'completed':
            return format_html(
                '<a class="button" href="{}">Download JSON</a>',
                reverse('admin:download_json', args=[obj.pk])
            )
        else:
            return obj.status
    
    action_buttons.short_description = 'Actions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:job_id>/start/',
                self.admin_site.admin_view(self.start_job_view),
                name='start_job',
            ),
            path(
                '<int:job_id>/download/',
                self.admin_site.admin_view(self.download_json_view),
                name='download_json',
            ),
        ]
        return custom_urls + urls
    
    def start_job_view(self, request, job_id):
        """View to start a site mapping job."""
        # Start the job processing
        result = start_job_processing(job_id)
        
        # Redirect back to the job list
        self.message_user(request, 'Job processing started.' if result else 'Failed to start job.')
        return HttpResponseRedirect(reverse('admin:site_mapper_sitemapjob_changelist'))
    
    def download_json_view(self, request, job_id):
        """View to download the JSON output of a completed job."""
        try:
            job = SiteMapJob.objects.get(id=job_id)
            # TODO: Implement file download
            self.message_user(request, 'Download functionality will be implemented soon.')
        except SiteMapJob.DoesNotExist:
            self.message_user(request, 'Job not found.')
        
        return HttpResponseRedirect(reverse('admin:site_mapper_sitemapjob_changelist'))
