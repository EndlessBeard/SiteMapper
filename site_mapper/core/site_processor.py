"""
Site Processor module for Site_Mapper2.
This module provides the main processing logic for the site mapping tool.
"""
import logging
import os
import time
import uuid
import asyncio
import threading
import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

from django.conf import settings
from django.utils import timezone

from site_mapper.models import SiteMapJob, Link
from site_mapper.core.crawler import WebCrawler
from site_mapper.core.link_extractor import LinkExtractor
from site_mapper.core.document_parser import DocumentParser
from site_mapper.core.link_manager import LinkManager

logger = logging.getLogger(__name__)

class SiteProcessor:
    """
    Main processor class for mapping websites.
    Manages the modular site mapping process with click depth tracking.
    """
    
    def __init__(self, job_id, max_workers=4):
        """
        Initialize the SiteProcessor.
        
        Args:
            job_id (int): ID of the SiteMapJob to process
            max_workers (int): Maximum number of worker threads
        """
        self.job_id = job_id
        self.max_workers = max_workers
        self.crawler = None
        self.link_manager = None
        self.job = None
        
        # Output directory for saving files
        self.output_dir = os.path.join(settings.MEDIA_ROOT, f'site_mapper/job_{job_id}')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Track output files by starting URL
        self.output_files = {}
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all required components for processing."""
        try:
            # Get the job
            self.job = SiteMapJob.objects.get(id=self.job_id)
            
            # Initialize link manager
            self.link_manager = LinkManager(self.job_id)
            
            # Initialize web crawler
            self.crawler = WebCrawler(headless=True)
            
            logger.info(f"Initialized components for job {self.job_id}")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            self.job.status = 'failed'
            self.job.save(update_fields=['status'])
            raise
    
    def _sanitize_url_for_filename(self, url):
        """
        Convert a URL to a valid filename by replacing invalid characters with underscores.
        
        Args:
            url (str): URL to sanitize
            
        Returns:
            str: Sanitized filename
        """
        # Parse the URL to get the netloc and path
        parsed = urlparse(url)
        base = parsed.netloc
        
        # Remove scheme, query parameters, and fragments
        path = parsed.path
        if path and path != '/':
            if path.endswith('/'):
                path = path[:-1]  # Remove trailing slash
            base += path
            
        # Replace invalid filename characters with underscores
        sanitized = re.sub(r'[\\/*?:"<>|]', '_', base)
        sanitized = re.sub(r'[. ]', '_', sanitized)  # Replace dots and spaces
        
        # Limit filename length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
            
        return sanitized
    
    # Use the link manager's normalize_url method to ensure consistency
    def _normalize_url(self, url):
        """
        Normalize a URL to ensure consistent matching across the application.
        Delegates to LinkManager's normalization to ensure consistency.
        
        Args:
            url (str): URL to normalize
            
        Returns:
            str: Normalized URL
        """
        # Use link_manager's implementation to ensure consistency
        return self.link_manager._normalize_url(url)
    
    def process(self):
        """
        Process the site mapping job.
        Executes the modular approach with click depth tracking.
        """
        try:
            # Initialize filter stats
            filtered_links_count = 0
            
            # Update job status
            self.job.status = 'processing'
            self.job.save(update_fields=['status'])
            
            # Phase 1: Process starting URLs at depth 0
            self._process_starting_urls()
            
            # Check if job has been requested to stop
            job_refresh = SiteMapJob.objects.get(id=self.job_id)
            if job_refresh.status == 'stopped':
                logger.info(f"Job {self.job_id} was requested to stop. Halting processing.")
                return
            
            # Process each depth level iteratively until max_depth is reached or no more links to process
            current_depth = 1
            while current_depth <= self.job.max_depth:
                # Check if job has been requested to stop
                job_refresh = SiteMapJob.objects.get(id=self.job_id)
                if job_refresh.status == 'stopped':
                    logger.info(f"Job {self.job_id} was requested to stop. Halting processing.")
                    return
                    
                self.job.current_depth = current_depth
                self.job.save(update_fields=['current_depth'])
                
                logger.info(f"Processing depth level {current_depth} for job {self.job_id}")
                
                # Process this depth level
                if not self._process_depth_level(current_depth):
                    # No links were processed at this depth, we can stop
                    logger.info(f"No more links to process at depth {current_depth}")
                    break
                
                current_depth += 1
            
            # Export results - one file per starting URL using the new starting_url field
            starting_urls = set(Link.objects.filter(job=self.job, depth=0).values_list('url', flat=True))
            
            for start_url in starting_urls:
                # Get links that belong to this starting URL
                links = Link.objects.filter(job=self.job, starting_url=start_url)
                
                # Generate filename based on the starting URL
                url_filename = self._sanitize_url_for_filename(start_url)
                output_file = os.path.join(self.output_dir, f"site_map_{url_filename}.json")
                
                # Store the mapping for future reference
                self.output_files[start_url] = output_file
                
                # Export only links related to this starting URL
                self.link_manager.export_links_to_json(list(links), output_file)
                logger.info(f"Exported links for starting URL {start_url} to {output_file}")
            
            # Update job status only if not manually stopped
            job_refresh = SiteMapJob.objects.get(id=self.job_id)
            if job_refresh.status != 'stopped':
                self.job.status = 'completed'
                self.job.save(update_fields=['status'])
            
            logger.info(f"Job {self.job_id} completed successfully. Filtered {filtered_links_count} links.")
        except Exception as e:
            logger.error(f"Error processing job {self.job_id}: {e}")
            self.job.status = 'failed'
            self.job.save(update_fields=['status'])
        finally:
            # Clean up
            if self.crawler:
                self.crawler.close()
    
    def _process_starting_urls(self):
        """
        Process the initial starting URLs at depth 0.
        Ensures each URL is treated as an independent starting point
        with its own hierarchy of links.
        """
        logger.info(f"Starting to process initial URLs at depth 0 for job {self.job_id}")
        
        # Get input URLs from job
        input_urls = self.job.start_urls.strip().split('\n')
        input_urls = [url.strip() for url in input_urls if url.strip()]
        
        if not input_urls:
            logger.warning("No input URLs provided")
            return
        
        # Log the number of starting URLs we're processing
        logger.info(f"Processing {len(input_urls)} starting URLs: {input_urls}")
        
        # Update depth tracking
        self.job.current_depth = 0
        self.job.save(update_fields=['current_depth'])
        
        # Process each starting URL sequentially to avoid race conditions
        processed_urls = []
        for i, url in enumerate(input_urls):
            try:
                normalized_url = self._normalize_url(url)
                logger.info(f"Processing starting URL {i+1}/{len(input_urls)}: {url} (normalized: {normalized_url})")
                
                # Process the starting URL - explicitly passing the starting URL as itself
                self._process_single_url(url, None, 0, url)
                
                # After processing, verify the URL was added successfully - use the normalized URL for lookups
                # Use a more flexible query that checks for the starting_url field
                link = Link.objects.filter(
                    job=self.job, 
                    url=normalized_url, 
                    depth=0, 
                    starting_url=normalized_url
                ).first()
                
                if not link:
                    logger.warning(f"Starting URL was not added to database: {url} (normalized: {normalized_url})")
                else:
                    logger.info(f"Successfully processed starting URL {i+1}: {url}")
                    processed_urls.append(url)
                    
            except Exception as e:
                logger.error(f"Error processing starting URL '{url}': {e}")
                # Continue with next URL rather than failing the entire job
        
        # Verify all starting URLs were processed 
        if len(processed_urls) != len(input_urls):
            missing_urls = [url for url in input_urls if url not in processed_urls]
            logger.warning(f"{len(missing_urls)} starting URLs were not successfully processed: {missing_urls}")
        else:
            logger.info(f"Successfully processed all {len(input_urls)} starting URLs")
            
        # Verify link counts for each starting URL to catch early issues
        for url in processed_urls:
            normalized_url = self._normalize_url(url)
            count = Link.objects.filter(job=self.job, starting_url=normalized_url).count()
            logger.info(f"Starting URL '{url}' has {count} associated links")
            
            # If no links other than the starting URL itself, report a warning
            if count <= 1:
                logger.warning(f"Starting URL '{url}' may have extraction issues - only has {count} links")
        
        logger.info(f"Completed processing initial URLs for job {self.job_id}")
    
    def _process_depth_level(self, depth):
        """
        Process all unprocessed links at a specific depth level.
        This includes both web pages and documents.
        
        Args:
            depth (int): The depth level to process
            
        Returns:
            bool: True if any links were processed, False otherwise
        """
        logger.info(f"Processing links at depth {depth} for job {self.job_id}")
        
        # First check if there are ANY links at this depth (processed or not)
        # This helps distinguish "no more to process" vs. "none were ever found"
        all_links_at_depth = Link.objects.filter(job=self.job, depth=depth).count()
        
        # Get all unprocessed links at this depth
        unprocessed_links = self.link_manager.get_unprocessed_links_by_depth(depth)
        
        if not unprocessed_links:
            if all_links_at_depth == 0 and depth == 1:
                # Special case: If we're at depth 1 and no links were found at all,
                # it might be an issue with link extraction, so log a warning
                logger.warning(f"No links found at depth {depth}. This may indicate an issue with link extraction.")
            else:
                logger.info(f"No unprocessed links at depth {depth}")
            
            if all_links_at_depth == 0 and depth < self.job.max_depth:
                # If no links at all were found at this depth but we haven't reached max_depth,
                # we can stop crawling since there's nothing more to discover
                logger.info(f"No links found at depth {depth}, stopping crawl")
                return False
            
            if depth < self.job.max_depth:
                # Check if there are any links at the next depth before stopping
                next_depth_links = Link.objects.filter(job=self.job, depth=depth+1).exists()
                if next_depth_links:
                    logger.info(f"Found links at next depth {depth+1}, continuing crawl")
                    return True
            
            return False
        
        # Group links by type
        pages = [link for link in unprocessed_links if link.type == 'page']
        documents = [link for link in unprocessed_links if link.type in ['pdf', 'docx', 'xlsx']]
        
        processed_count = 0
        
        # Process pages
        if pages:
            logger.info(f"Processing {len(pages)} pages at depth {depth}")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._process_single_page, link, depth) for link in pages]
                
                for future in futures:
                    try:
                        future.result()
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Error in page processing thread: {e}")
        
        # Process documents
        if documents:
            logger.info(f"Processing {len(documents)} documents at depth {depth}")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._process_single_document, link, depth) for link in documents]
                
                for future in futures:
                    try:
                        future.result()
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Error in document processing thread: {e}")
        
        logger.info(f"Processed {processed_count} links at depth {depth}")
        return processed_count > 0 or all_links_at_depth > 0
    
    def _process_single_url(self, url, parent_id=None, depth=0, starting_url=None):
        """Process a single URL."""
        # For depth 0, the URL is its own starting URL
        if depth == 0:
            starting_url = url
            
        # Determine if this is a page or document
        link_type = self._determine_link_type(url)
        
        # Get the page title to use as link text (if it's a page)
        link_text = None
        if link_type == 'page':
            try:
                # Try to fetch just the title
                _, page_title, _ = self.crawler.fetch_page(url)
                if page_title:
                    link_text = page_title
            except:
                pass
        
        # Create link entry if it doesn't exist
        link_id = self.link_manager.add_link(
            url=url,
            link_text=link_text or url,  # Use page title if available, otherwise URL
            link_type=link_type,
            parent_id=parent_id,
            depth=depth,
            starting_url=starting_url
        )
        
        if not link_id:
            logger.warning(f"Failed to create link for URL: {url}")
            return
        
        # Get link object
        try:
            link = Link.objects.get(id=link_id)
            
            # Process based on type
            if link_type == 'page':
                self._process_single_page(link, depth, starting_url)
            else:
                self._process_single_document(link, depth, starting_url)
        except Link.DoesNotExist:
            logger.warning(f"Link object not found for ID: {link_id}")
    
    def _process_single_page(self, link, depth, starting_url=None):
        """
        Process a single webpage.
        
        Args:
            link (Link): Link object for the page
            depth (int): Depth level of this page
            starting_url (str, optional): The starting URL this link belongs to
        """
        url = link.url
        logger.info(f"Processing page: {url} at depth {depth}")
        
        # Use the link's starting_url if not provided
        if starting_url is None and hasattr(link, 'starting_url'):
            starting_url = link.starting_url
        
        try:
            # Fetch the page
            page_content, page_title, soup = self.crawler.fetch_page(url)
            
            if not soup:
                logger.warning(f"Failed to fetch page: {url}")

                # Mark as processed and set type to 'broken'
                link.processed = True
                link.type = 'broken'  # Change type to 'broken'
                link.file_path = None  # Ensure no path for failed fetches

                link.save(update_fields=['processed', 'type', 'file_path'])

                return
            
            # Save the page content
            page_filename = f"page_{uuid.uuid4().hex}.html"
            page_path = os.path.join(self.output_dir, page_filename)
            
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(page_content)
            
            # Store the current link ID for child links to reference
            current_link_id = link.id
            
            # Reload the link object to ensure it has a primary key
            try:
                link = Link.objects.get(id=link.id)
                # Update link with file path and title if available
                link.file_path = page_path
                if page_title and not link.link_text:
                    link.link_text = page_title
                link.save()
            except Link.DoesNotExist:
                logger.warning(f"Link not found when updating file path: {url}")
                return
            
            # Extract links
            base_url = url
            link_extractor = LinkExtractor(base_url)
            extracted_links = link_extractor.extract_links(soup)
            
            # Filter document links
            filtered_docs = [link_data for link_data in extracted_links['documents'] 
                             if not self.link_manager.should_filter_url(link_data['url'])]
            
            # Filter content links
            filtered_content = [link_data for link_data in extracted_links['content'] 
                               if not self.link_manager.should_filter_url(link_data['url'])]
            
            # Add document links - they'll be at depth+1
            self.link_manager.add_links(
                filtered_docs, 
                parent_id=current_link_id,
                depth=depth+1,
                starting_url=starting_url
            )
            
            # Add content links (excluding navigation) - they'll be at depth+1
            self.link_manager.add_links(
                filtered_content, 
                parent_id=current_link_id,
                depth=depth+1,
                starting_url=starting_url
            )
            
            # Mark page as processed
            self.link_manager.mark_as_processed(current_link_id)
            
            logger.info(f"Processed page: {url} at depth {depth}")
        except Exception as e:
            logger.error(f"Error processing page {url}: {e}")
            # Still mark as processed to avoid reprocessing
            self.link_manager.mark_as_processed(link.id)
    
    def _process_single_document(self, link, depth, starting_url=None):
        """
        Process a single document.
        
        Args:
            link (Link): Link object representing the document
            depth (int): Depth level of this document
            starting_url (str, optional): The starting URL this link belongs to
        """
        url = link.url
        logger.info(f"Processing document: {url} at depth {depth}")
        
        # Use the link's starting_url if not provided
        if starting_url is None and hasattr(link, 'starting_url'):
            starting_url = link.starting_url
        
        try:
            # Download the document if not already downloaded
            file_path = link.file_path
            if not file_path or not os.path.exists(file_path):
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path) or f"document_{uuid.uuid4().hex}"
                
                if not filename.lower().endswith(('.pdf', '.docx', '.xlsx', '.xls', '.doc')):
                    # Add appropriate extension based on link type
                    if link.type == 'pdf':
                        filename += '.pdf'
                    elif link.type == 'docx':
                        filename += '.docx'
                    elif link.type == 'xlsx':
                        filename += '.xlsx'
                
                file_path = self.crawler.download_file(
                    url=url,
                    destination_dir=self.output_dir,
                    filename=filename
                )
                
                #unused?
                def _is_valid_content_type(self, file_path, expected_type):
                    """
                    Check if the downloaded file is of the expected content type.
                    
                    Args:
                        file_path (str): Path to the downloaded file
                        expected_type (str): Expected type ('pdf', 'docx', 'xlsx')
                        
                    Returns:
                        bool: True if file exists and matches expected type, False otherwise
                    """
                    if not os.path.exists(file_path):
                        return False
                        
                    # Simple extension check
                    if expected_type == 'pdf' and file_path.lower().endswith('.pdf'):
                        return True
                    elif expected_type == 'docx' and file_path.lower().endswith(('.docx', '.doc')):
                        return True
                    elif expected_type == 'xlsx' and file_path.lower().endswith(('.xlsx', '.xls')):
                        return True
                        
                    # Could add more sophisticated content type checking here with libraries
                    # like python-magic or checking file headers
                        
                    return False
                
                # Reload the link object to ensure it has a primary key
                try:
                    link = Link.objects.get(id=link.id)
                    # Update file path
                    link.file_path = file_path
                    link.save()
                except Link.DoesNotExist:
                    logger.warning(f"Link not found when updating file path: {url}")
                    return
       

            # Parse the document
            doc_parser = DocumentParser(base_url=url)
            result = doc_parser.parse(file_path)
            
            if not result['links']:
                logger.info(f"No links found in document: {url}")
                self.link_manager.mark_as_processed(link.id)
                return
            
            # Process found links - filter and then process at depth+1
            links_data = []
            for url_data in result['links']:
                if not self.link_manager.should_filter_url(url_data['url']):
                    links_data.append({
                        'url': url_data['url'],
                        'text': url_data['text'],
                        'type': self._determine_link_type(url_data['url'])
                    })
            
            # Add links to registry with the same starting_url
            self.link_manager.add_links(
                links_data, 
                parent_id=link.id,
                depth=depth+1,
                starting_url=starting_url
            )
            
            # Mark document as processed
            self.link_manager.mark_as_processed(link.id)
            
            logger.info(f"Processed document: {url}")
        except Exception as e:
            logger.error(f"Error processing document {url}: {e}")
            # Still mark as processed to avoid reprocessing
            self.link_manager.mark_as_processed(link.id)
    
    def _determine_link_type(self, url):
        """
        Determine the type of link based on the URL.
        
        Args:
            url (str): URL to analyze
            
        Returns:
            str: Type of link (pdf, docx, xlsx, page)
        """
        if not url:
            return 'page'
        
        # Check for document extensions
        lower_url = url.lower()
        
        if lower_url.endswith('.pdf'):
            return 'pdf'
        elif lower_url.endswith('.docx') or lower_url.endswith('.doc'):
            return 'docx'
        elif lower_url.endswith('.xlsx') or lower_url.endswith('.xls'):
            return 'xlsx'
        else:
            return 'page'
    
    def process_next_depth(self):
        """
        Process the next depth level only.
        This method is used for the modular approach to run one depth at a time.
        
        Returns:
            bool: True if processing occurred, False if no more depths to process
        """
        next_depth = self.job.current_depth + 1
        
        # Check if we've already reached max depth
        if next_depth > self.job.max_depth:
            logger.info(f"Already reached max depth {self.job.max_depth}")
            return False
            
        # Process this depth level
        self.job.current_depth = next_depth
        self.job.save(update_fields=['current_depth'])
        
        logger.info(f"Processing next depth level {next_depth} for job {self.job_id}")
        result = self._process_depth_level(next_depth)
        
        # Export partial results - one file per starting URL using direct querying (consistent with process method)
        starting_urls = set(Link.objects.filter(job=self.job, depth=0).values_list('url', flat=True))
        
        for start_url in starting_urls:
            # Get links that belong to this starting URL
            links = Link.objects.filter(job=self.job, starting_url=start_url)
            
            # Generate filename based on the starting URL
            url_filename = self._sanitize_url_for_filename(start_url)
            output_file = os.path.join(self.output_dir, f"site_map_{url_filename}.json")
            
            # Store the mapping for future reference
            self.output_files[start_url] = output_file
            
            # Export only links related to this starting URL
            self.link_manager.export_links_to_json(links, output_file)  # Removed list() conversion
            logger.info(f"Exported partial results for starting URL {start_url} to {output_file}")
        
        return result


# Asynchronous job processing function for running in background
def process_job_async(job_id):
    """
    Process a site mapping job asynchronously.
    
    Args:
        job_id (int): ID of the SiteMapJob to process
    """
    processor = SiteProcessor(job_id)
    
    try:
        processor.process()
    except Exception as e:
        logger.error(f"Error in async job processing: {e}")
        
        # Update job status to failed
        try:
            job = SiteMapJob.objects.get(id=job_id)
            job.status = 'failed'
            job.save(update_fields=['status'])
        except:
            pass


# Function to start a job in a background thread
def start_job_processing(job_id):
    """
    Start processing a job in a background thread.
    Will process all depth levels automatically.
    
    Args:
        job_id (int): ID of the SiteMapJob to process
        
    Returns:
        bool: True if job was started, False otherwise
    """
    try:
        job = SiteMapJob.objects.get(id=job_id)
        
        if job.status != 'pending':
            logger.warning(f"Job {job_id} is not in pending status, current status: {job.status}")
            return False
        
        # Start processing in a background thread using the process() method
        # which automatically handles all depth levels
        thread = threading.Thread(target=process_job_async, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started background processing for job {job_id}")
        return True
        
    except SiteMapJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error starting job {job_id}: {e}")
        return False


# Function to run a single depth iteration for a job
def process_next_depth(job_id):
    """
    Process the next depth level for a job.
    
    Args:
        job_id (int): ID of the SiteMapJob to process
        
    Returns:
        bool: True if depth was processed, False if no more depths to process
    """
    try:
        job = SiteMapJob.objects.get(id=job_id)
        
        if job.status != 'processing':
            # If the job is pending, start it first (will process depth 0)
            if job.status == 'pending':
                start_job_processing(job_id)
                return True
            else:
                logger.warning(f"Job {job_id} is not in processing status, current status: {job.status}")
                return False
        
        # Start processing the next depth in a background thread
        def run_next_depth():
            try:
                processor = SiteProcessor(job_id)
                result = processor.process_next_depth()
                
                # If no more depths to process, mark as completed
                if not result:
                    job.status = 'completed'
                    job.save(update_fields=['status'])
            except Exception as e:
                logger.error(f"Error processing next depth for job {job_id}: {e}")
                job.status = 'failed'
                job.save(update_fields=['status'])
        
        # Start the thread
        thread = threading.Thread(target=run_next_depth)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started processing next depth for job {job_id}")
        return True
        
    except SiteMapJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error processing next depth for job {job_id}: {e}")
        return False