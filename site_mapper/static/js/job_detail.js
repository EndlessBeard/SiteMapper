function updateJobStatus() {
    const jobId = document.getElementById('job-id').value;
    
    fetch(`/api/jobs/${jobId}/status/`)
        .then(response => response.json())
        .then(data => {
            // Update status display
            document.getElementById('job-status').textContent = data.status;
            
            // Apply appropriate styling based on status
            const statusElement = document.getElementById('job-status');
            statusElement.className = ''; // Reset classes
            statusElement.classList.add(`status-${data.status.toLowerCase()}`);
            
            // If job completed or failed, update additional info
            if (data.status === 'completed' || data.status === 'failed') {
                if (data.end_time) {
                    document.getElementById('job-end-time').textContent = data.end_time;
                }
                if (data.output_files) {
                    const filesContainer = document.getElementById('output-files');
                    filesContainer.innerHTML = '';
                    data.output_files.forEach(file => {
                        const link = document.createElement('a');
                        link.href = file.url;
                        link.textContent = file.name;
                        filesContainer.appendChild(link);
                        filesContainer.appendChild(document.createElement('br'));
                    });
                }
            }
            
            // Continue polling if job is still in progress
            if (data.status === 'processing' || data.status === 'queued') {
                setTimeout(updateJobStatus, 5000); // Check every 5 seconds
            }
        })
        .catch(error => console.error('Error checking job status:', error));
}

// Start polling when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const jobStatus = document.getElementById('job-status').textContent;
    if (jobStatus === 'processing' || jobStatus === 'queued') {
        // Start polling if job is in progress
        setTimeout(updateJobStatus, 5000);
    }
});