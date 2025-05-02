document.addEventListener('DOMContentLoaded', function() {
    console.log("Job detail JS loaded");
    
    // Get job status and set up polling if necessary
    const jobStatusElement = document.getElementById('job-status');
    if (jobStatusElement) {
        const jobStatus = jobStatusElement.textContent.trim();
        if (jobStatus === 'processing' || jobStatus === 'pending') {
            startStatusPolling();
        }
    }
    
    // Set up modal triggers
    const docxButtons = document.querySelectorAll('.generate-docx-btn');
    docxButtons.forEach(button => {
        button.addEventListener('click', function() {
            const jobId = document.getElementById('job-id-field').value;
            showDocxFiles(jobId);
        });
    });
});

function startStatusPolling() {
    const jobId = document.getElementById('job-id-field').value;
    updateJobStatus();
    setInterval(updateJobStatus, 5000);
}

function updateJobStatus() {
    const jobId = document.getElementById('job-id-field').value;
    const statusUrl = `/site_mapper/jobs/${jobId}/status/`;
    
    fetch(statusUrl)
        .then(response => response.json())
        .then(data => {
            // Update UI with job status data
            console.log("Job status updated:", data);
            
            // Update relevant UI elements
            const statusElement = document.getElementById('job-status');
            if (statusElement && data.status) {
                statusElement.textContent = data.status;
                
                // Update badge class based on status
                if (statusElement.classList) {
                    // Remove all status classes
                    statusElement.classList.remove('bg-primary', 'bg-success', 'bg-danger', 'bg-secondary');
                    
                    // Add appropriate class
                    switch(data.status) {
                        case 'processing': statusElement.classList.add('bg-primary'); break;
                        case 'completed': statusElement.classList.add('bg-success'); break;
                        case 'failed': statusElement.classList.add('bg-danger'); break;
                        default: statusElement.classList.add('bg-secondary');
                    }
                }
            }
            
            // Update other statistics elements
            updateElementIfExists('total-links', data.total_links);
            updateElementIfExists('processed-links', data.processed_links);
            updateElementIfExists('total-pages', data.total_pages);
            updateElementIfExists('total-documents', data.total_documents);
            updateElementIfExists('total-broken', data.total_broken);
            updateElementIfExists('current-depth', data.current_depth);
        })
        .catch(error => {
            console.error("Error updating job status:", error);
        });
}

function updateElementIfExists(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined) {
        element.textContent = value;
    }
}

function showDocxFiles(jobId) {
    console.log("showDocxFiles called with jobId:", jobId);
    
    // If jobId is undefined, try to get it from hidden field
    if (!jobId) {
        const jobIdField = document.getElementById('job-id-field');
        if (jobIdField) {
            jobId = jobIdField.value;
            console.log("Retrieved jobId from hidden field:", jobId);
        } else {
            console.error("Job ID is undefined and no job-id-field found");
            alert("Error: Could not determine job ID. Please reload the page.");
            return;
        }
    }
    
    // Get modal elements
    const modal = new bootstrap.Modal(document.getElementById('docxFilesModal'));
    const loadingSpinner = document.getElementById('docxLoadingSpinner');
    const filesList = document.getElementById('docxFilesList');
    const filesTable = document.getElementById('docxFilesTable');
    const filesError = document.getElementById('docxFilesError');
    
    // Check if all elements exist
    if (!modal || !loadingSpinner || !filesList || !filesTable || !filesError) {
        console.error("One or more required modal elements not found");
        alert("Error: Modal elements not found. Please reload the page.");
        return;
    }
    
    // Reset modal state
    loadingSpinner.classList.remove('d-none');
    filesList.classList.add('d-none');
    filesError.classList.add('d-none');
    filesError.textContent = '';
    filesTable.innerHTML = '';
    
    // Show modal
    modal.show();
    
    // Build URL with proper path
    const docxConversionUrl = `/site_mapper/jobs/${jobId}/to-docx/`;
    console.log("Fetching DOCX files from:", docxConversionUrl);
    
    // Make AJAX request
    fetch(docxConversionUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading spinner
            loadingSpinner.classList.add('d-none');
            
            if (data.success) {
                // Update modal title with job name
                const modalTitle = document.getElementById('docxFilesModalLabel');
                if (modalTitle) {
                    modalTitle.textContent = `DOCX Files for ${data.job_name || 'Job'}`;
                }
                
                if (data.files && data.files.length > 0) {
                    // Show files list
                    filesList.classList.remove('d-none');
                    
                    // Create a row for each file
                    data.files.forEach(file => {
                        const row = document.createElement('tr');
                        
                        // File name cell
                        const nameCell = document.createElement('td');
                        nameCell.textContent = file.name;
                        row.appendChild(nameCell);
                        
                        // File size cell
                        const sizeCell = document.createElement('td');
                        sizeCell.textContent = file.size;
                        row.appendChild(sizeCell);
                        
                        // Actions cell
                        const actionsCell = document.createElement('td');
                        const downloadLink = document.createElement('a');
                        downloadLink.href = file.url;
                        downloadLink.className = 'btn btn-sm btn-primary';
                        downloadLink.innerHTML = '<i class="fas fa-download"></i> Download';
                        actionsCell.appendChild(downloadLink);
                        row.appendChild(actionsCell);
                        
                        filesTable.appendChild(row);
                    });
                } else {
                    // No files found
                    filesError.textContent = "No DOCX files were generated.";
                    filesError.classList.remove('d-none');
                }
            } else {
                // Show error
                filesError.textContent = data.error || "An error occurred while generating DOCX files.";
                filesError.classList.remove('d-none');
            }
        })
        .catch(error => {
            // Hide loading spinner
            loadingSpinner.classList.add('d-none');
            
            // Show error
            filesError.textContent = "Error: " + error.message;
            filesError.classList.remove('d-none');
            console.error('Error:', error);
        });
}