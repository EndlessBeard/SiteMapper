from django.http import HttpResponse, JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json
import time
import logging
from .models import SiteMapJob, Link
from .core.site_processor import SiteProcessor
from .core.crawler import WebCrawler
from .core.document_parser import DocumentParser
from .core.docx_converter import json_to_docx, process_job_to_docx
import tempfile

def dashboard(request):
    """Main dashboard view showing active jobs and stats."""
    jobs = SiteMapJob.objects.all().order_by('-created_at')
    
    # Count jobs by status
    status_counts = {
        'pending': SiteMapJob.objects.filter(status='pending').count(),
        'processing': SiteMapJob.objects.filter(status='processing').count(),
        'completed': SiteMapJob.objects.filter(status='completed').count(),
        'failed': SiteMapJob.objects.filter(status='failed').count(),
    }
    
    # Get the total of links by type across all jobs
    link_counts = {
        'pdf': Link.objects.filter(type='pdf').count(),
        'docx': Link.objects.filter(type='docx').count(),
        'xlsx': Link.objects.filter(type='xlsx').count(),
        'page': Link.objects.filter(type='page').count(),
        'total': Link.objects.count(),
        'processed': Link.objects.filter(processed=True).count(),
    }
    
    # Add per-job link counts
    job_link_counts = {}
    for job in jobs:
        job_link_counts[job.id] = {
            'total': Link.objects.filter(job=job).count(),
            'processed': Link.objects.filter(job=job, processed=True).count(),
        }
    
    context = {
        'jobs': jobs,
        'status_counts': status_counts,
        'link_counts': link_counts,
        'job_link_counts': job_link_counts,
    }
    
    return render(request, 'site_mapper/dashboard.html', context)

def job_create(request):
    """View to create a new site mapping job."""
    if request.method == 'POST':
        name = request.POST.get('name')
        start_urls = request.POST.get('start_urls')
        output_file = request.POST.get('output_file', 'site_map.json')
        max_depth = request.POST.get('max_depth', 3)
        
        try:
            max_depth = int(max_depth)
        except (TypeError, ValueError):
            max_depth = 3  # Default to 3 if invalid value
            
        if not name or not start_urls:
            messages.error(request, "Job name and start URLs are required.")
            return redirect('site_mapper:job_create')
        
        # Create new job
        job = SiteMapJob.objects.create(
            name=name,
            start_urls=start_urls,
            output_file=output_file,
            max_depth=max_depth
        )
        
        messages.success(request, f"Job '{name}' created successfully.")
        return redirect('site_mapper:job_detail', job_id=job.id)
    
    return render(request, 'site_mapper/job_create.html')

def job_detail(request, job_id):
    """View to show details for a specific job."""
    job = get_object_or_404(SiteMapJob, id=job_id)
    
    # Get links associated with this job only
    links = Link.objects.filter(job=job).order_by('depth', 'created_at')[:100]  # Limit to 100 for performance
    
    # Count links by type for THIS JOB only
    link_type_counts = {
        'pdf': Link.objects.filter(job=job, type='pdf').count(),
        'docx': Link.objects.filter(job=job, type='docx').count(),
        'xlsx': Link.objects.filter(job=job, type='xlsx').count(),
        'page': Link.objects.filter(job=job, type='page').count(),
    }
    
    # Count total documents (PDF, DOCX, XLSX)
    total_documents = link_type_counts['pdf'] + link_type_counts['docx'] + link_type_counts['xlsx']
    
    # Count links by depth for THIS JOB only (we'll keep this for reference but won't display it in the UI)
    depth_counts = {}
    for i in range(job.max_depth + 1):
        depth_counts[i] = {
            'total': Link.objects.filter(job=job, depth=i).count(),
            'processed': Link.objects.filter(job=job, depth=i, processed=True).count()
        }
    
    if job.total_links > 0:
        progress_percent = int((job.processed_links / job.total_links) * 100)
    else:
        progress_percent = 0
        
    context = {
        'job': job,
        'links': links,
        'depth_counts': depth_counts,
        'progress_percent': progress_percent,
        'link_type_counts': link_type_counts,
        'total_documents': total_documents,
    }
    
    return render(request, 'site_mapper/job_detail.html', context)

def start_job_processing(job_id):
    """Helper function to start processing a job."""
    try:
        job = SiteMapJob.objects.get(id=job_id)
        job.status = 'processing'
        job.save()
        
        # Start the background job processing using the site_processor module's function
        # This will process all depth levels automatically
        from .core.site_processor import process_job_async
        import threading
        
        # Start processing in a background thread
        thread = threading.Thread(target=process_job_async, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        logging.info(f"Started background processing for job {job_id}")
        return True
    except Exception as e:
        logging.error(f"Error starting job {job_id}: {str(e)}")
        return False

def job_start(request, job_id):
    """View to start processing a job."""
    job = get_object_or_404(SiteMapJob, id=job_id)
    
    if job.status != 'pending':
        messages.warning(request, f"Job '{job.name}' is already {job.status}.")
        return redirect('site_mapper:job_detail', job_id=job.id)
    
    # Start job processing
    success = start_job_processing(job.id)
    
    if success:
        messages.success(request, f"Job '{job.name}' started successfully.")
    else:
        messages.error(request, f"Failed to start job '{job.name}'.")
    
    return redirect('site_mapper:job_detail', job_id=job.id)

def job_process_next_depth(request, job_id):
    """View to process the next depth level of a job."""
    job = get_object_or_404(SiteMapJob, id=job_id)
    
    if job.status not in ['pending', 'processing']:
        messages.warning(request, f"Job '{job.name}' is {job.status} and cannot be processed further.")
        return redirect('site_mapper:job_detail', job_id=job.id)
    
    # Process next depth level
    success = process_next_depth(job.id)
    
    if success:
        messages.success(request, f"Processing depth level {job.current_depth + 1} for job '{job.name}'.")
    else:
        messages.error(request, f"Failed to process next depth level for job '{job.name}'.")
    
    return redirect('site_mapper:job_detail', job_id=job.id)

def process_next_depth(job_id):
    """Helper function to process the next depth level of a job."""
    try:
        job = SiteMapJob.objects.get(id=job_id)
        
        # Initialize site processor
        processor = SiteProcessor(job)
        
        # Process the next depth level
        next_depth = job.current_depth + 1
        if next_depth <= job.max_depth:
            return processor.process_depth(next_depth)
        else:
            # Job is complete if we've reached max depth
            job.status = 'completed'
            job.save()
            return True
    except Exception as e:
        logging.error(f"Error processing next depth for job {job_id}: {str(e)}")
        return False

def job_status(request, job_id):
    """AJAX endpoint to get current job status and progress."""
    try:
        job = SiteMapJob.objects.get(id=job_id)
        
        if job.total_links > 0:
            progress_percent = int((job.processed_links / job.total_links) * 100)
        else:
            progress_percent = 0
            
        # Count links by type for this job
        link_type_counts = {
            'pdf': Link.objects.filter(job=job, type='pdf').count(),
            'docx': Link.objects.filter(job=job, type='docx').count(),
            'xlsx': Link.objects.filter(job=job, type='xlsx').count(),
            'page': Link.objects.filter(job=job, type='page').count(),
        }
        
        # Count total documents (PDF, DOCX, XLSX)
        total_documents = link_type_counts['pdf'] + link_type_counts['docx'] + link_type_counts['xlsx']
        
        data = {
            'status': job.status,
            'total_links': job.total_links,
            'processed_links': job.processed_links,
            'progress_percent': progress_percent,
            'current_depth': job.current_depth,
            'max_depth': job.max_depth,
            'link_type_counts': link_type_counts,
            'total_documents': total_documents,
            'total_pages': link_type_counts['page'],
        }
        
        return JsonResponse(data)
    except SiteMapJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)

def job_download(request, job_id):
    """View to download the JSON output of a completed job."""
    job = get_object_or_404(SiteMapJob, id=job_id)
    
    if job.status != 'completed':
        messages.warning(request, f"Job '{job.name}' is not completed yet.")
        return redirect('site_mapper:job_detail', job_id=job.id)
    
    # Build the path to the output file
    output_dir = os.path.join(settings.MEDIA_ROOT, f'site_mapper/job_{job_id}')
    output_file = os.path.join(output_dir, job.output_file)
    
    if not os.path.exists(output_file):
        messages.error(request, f"Output file not found for job '{job.name}'.")
        return redirect('site_mapper:job_detail', job_id=job.id)
    
    # Return the file as a download
    response = FileResponse(open(output_file, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{job.output_file}"'
    return response

def job_to_docx(request, job_id):
    """Convert job results to DOCX format and show list in popup."""
    try:
        # Get the job
        job = get_object_or_404(SiteMapJob, id=job_id)
        
        # Check if we're downloading a specific file
        docx_filename = request.GET.get('download')
        if docx_filename:
            # User is requesting a specific file download
            # Files are stored directly in the job directory
            docx_path = os.path.join(settings.MEDIA_ROOT, f'site_mapper/job_{job_id}', docx_filename)
            
            if os.path.exists(docx_path):
                response = FileResponse(open(docx_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = f'attachment; filename="{docx_filename}"'
                return response
            else:
                messages.error(request, f"File not found: {docx_filename}")
                return redirect('site_mapper:job_detail', job_id=job_id)
        
        # Use the process_job_to_docx function to convert all site maps for this job
        docx_files = process_job_to_docx(job_id)
        
        if not docx_files:
            messages.error(request, "No site maps found for this job.")
            return redirect('site_mapper:job_detail', job_id=job_id)
        
        # Prepare file list as JSON for the modal
        file_list = []
        for path in docx_files:
            filename = os.path.basename(path)
            file_size = os.path.getsize(path) / 1024  # Size in KB
            file_list.append({
                'name': filename,
                'size': f"{file_size:.1f} KB",
                'url': f"{reverse('site_mapper:job_to_docx', args=[job_id])}?download={filename}"
            })
        
        # Return JSON response for AJAX request
        return JsonResponse({
            'success': True,
            'files': file_list,
            'job_name': job.name
        })
        
    except Exception as e:
        if request.GET.get('download'):
            messages.error(request, f"Error downloading DOCX: {str(e)}")
            return redirect('site_mapper:job_detail', job_id=job_id)
        else:
            # Return JSON error for AJAX request
            return JsonResponse({'success': False, 'error': str(e)})

def job_stop(request, job_id):
    """Stop a running job"""
    try:
        job = SiteMapJob.objects.get(id=job_id)
        
        if job.status == 'processing':
            job.status = 'stopped'
            job.save(update_fields=['status'])
            messages.success(request, f"Job '{job.name}' has been marked for stopping. It will stop at the next checkpoint.")
        else:
            messages.warning(request, f"Job '{job.name}' is not running (status: {job.status}).")
            
        return redirect('site_mapper:job_detail', job_id=job_id)
    except SiteMapJob.DoesNotExist:
        messages.error(request, "Job not found.")
        return redirect('site_mapper:dashboard')

def job_delete(request, job_id):
    """View to delete a job and its associated links."""
    job = get_object_or_404(SiteMapJob, id=job_id)
    
    if job.status == 'processing':
        messages.error(request, f"Cannot delete job '{job.name}' while it's running. Stop it first.")
        return redirect('site_mapper:job_detail', job_id=job.id)
    
    job_name = job.name
    
    # Delete any stored files for this job
    job_dir = os.path.join(settings.MEDIA_ROOT, 'site_mapper', f'job_{job_id}')
    if os.path.exists(job_dir):
        import shutil
        try:
            shutil.rmtree(job_dir)
        except OSError as e:
            logging.error(f"Error deleting job directory: {str(e)}")
    
    # Delete the job (this will also delete related links due to the CASCADE setting)
    job.delete()
    
    messages.success(request, f"Job '{job_name}' and all associated data have been deleted.")
    return redirect('site_mapper:dashboard')

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

@login_required
@require_GET
def job_status_api(request, job_id):
    """API endpoint to get the current status of a job."""
    try:
        # Remove the user filter here too
        job = SiteMapJob.objects.get(id=job_id)
        
        # Prepare the response data
        data = {
            'status': job.status,
            'start_time': job.start_time.strftime('%Y-%m-%d %H:%M:%S') if job.start_time else None,
            'end_time': job.end_time.strftime('%Y-%m-%d %H:%M:%S') if job.end_time else None,
        }
        
        # Add output files if job is completed
        if job.status == 'completed':
            output_dir = os.path.join(settings.MEDIA_ROOT, f'site_mapper/job_{job_id}')
            if os.path.exists(output_dir):
                files = []
                for file_name in os.listdir(output_dir):
                    if file_name.startswith('site_map_') and (file_name.endswith('.json') or file_name.endswith('.docx')):
                        files.append({
                            'name': file_name,
                            'url': f'{settings.MEDIA_URL}site_mapper/job_{job_id}/{file_name}'
                        })
                data['output_files'] = files
        
        return JsonResponse(data)
    except SiteMapJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
