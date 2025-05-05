"""
Link Manager module for Site_Mapper2.
This module provides link tracking and management for the site mapping process.
"""
import json
import logging
import time
import urllib.parse
from django.db import transaction
from django.db.utils import OperationalError
from site_mapper.models import SiteMapJob, Link

logger = logging.getLogger(__name__)

class LinkManager:
    """
    Manages links discovered during site mapping.
    Handles adding links, tracking processing status, and exporting results.
    """
    
    def __init__(self, job_id):
        """Initialize the LinkManager."""
        self.job_id = job_id
        self.job = SiteMapJob.objects.get(id=job_id)
        
        # Cache the filters for better performance
        from site_mapper.models import SiteFilter
        self.filters = list(SiteFilter.objects.values_list('url', flat=True))
    
    def _normalize_url(self, url):
        """
        Normalize a URL to ensure consistent matching.
        
        Args:
            url (str): URL to normalize
            
        Returns:
            str: Normalized URL
        """
        if not url:
            return url
            
        # Parse URL
        parsed = urllib.parse.urlparse(url)
        
        # Normalize components
        netloc = parsed.netloc.lower()
        
        # Handle path - remove trailing slashes except for root path
        path = parsed.path
        if path and path != '/' and path.endswith('/'):
            path = path.rstrip('/')
            
        # Rebuild URL with normalized components
        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),  # Normalize protocol
            netloc,                 # Lowercase domain
            path,                   # Path with trailing slash handling
            parsed.params,          # Keep params unchanged
            parsed.query,           # Keep query string unchanged
            ''                      # Remove fragments
        ))
        
        return normalized
    
    def add_link(self, url, link_type, parent_id=None, depth=0, link_text=None, starting_url=None):
        """
        Add a single link to the link registry.
        
        Args:
            url (str): URL of the link
            link_type (str): Type of link (page, pdf, docx, xlsx)
            parent_id (UUID, optional): UUID of parent link
            depth (int): Depth level of the link
            link_text (str, optional): Text of the link
            starting_url (str, optional): The starting URL this link belongs to
        
        Returns:
            UUID: UUID of the created or existing link
        """
        if not url:
            return None
        
        # For depth 0 starting URLs, don't apply filtering
        if depth == 0:
            # Process normally without filtering
            pass
        else:
            # Apply filtering check
            if self.should_filter_url(url):
                return None

        if link_type not in ['page', 'pdf', 'docx', 'xlsx', 'other', 'broken']:
            logger.warning(f"Invalid link type: {link_type}")
            return None

        normalized_url = self._normalize_url(url)
        normalized_starting_url = self._normalize_url(starting_url) if starting_url else None
        
        logger.debug(f"Adding link: {url} (normalized: {normalized_url}), starting_url: {starting_url}, depth: {depth}")
        
        try:
            with transaction.atomic():
                # Special handling for starting URLs (depth 0)
                if depth == 0:
                    # For depth 0, this URL is its own starting URL
                    normalized_starting_url = normalized_url
                    
                    # Check if this starting URL already exists
                    existing_links = Link.objects.select_for_update().filter(
                        job=self.job,
                        url=normalized_url,
                        depth=0
                    )
                    
                    if existing_links.exists():
                        logger.info(f"Starting URL already exists: {url}")
                        existing_link = existing_links.first()
                        
                        # Ensure starting_url is set correctly
                        if not existing_link.starting_url or existing_link.starting_url != normalized_url:
                            existing_link.starting_url = normalized_url
                            existing_link.save(update_fields=['starting_url'])
                            logger.info(f"Updated starting_url for existing link: {url}")
                            
                        return existing_link.id
                else:
                    # For non-depth-0 links, check if the URL already exists for this job
                    existing_links = Link.objects.select_for_update().filter(
                        job=self.job,
                        url=normalized_url
                    )
                
                    if existing_links.exists():
                        existing_link = existing_links.first()
                        
                        # If we found a shorter path to this link, update it
                        if existing_link.depth > depth:
                            logger.info(f"Updating link {url} from depth {existing_link.depth} to depth {depth}")
                            existing_link.depth = depth
                            existing_link.parent_id = parent_id
                            
                            # Always ensure starting_url is set
                            if normalized_starting_url and not existing_link.starting_url:
                                existing_link.starting_url = normalized_starting_url
                                
                            existing_link.save(update_fields=['depth', 'parent_id', 'starting_url'])
                        
                        # Return the existing UUID - we don't create a duplicate
                        return existing_link.id
                
                # Create the link - with normalized URL but preserve the original URL in link_text if not provided
                link = Link(
                    job=self.job,
                    url=normalized_url,
                    type=link_type,
                    parent_id=parent_id,
                    depth=depth,
                    link_text=link_text or url,
                    starting_url=normalized_starting_url
                )
                link.save()
                
                # Log creation
                logger.debug(f"Created new link: {url}, type: {link_type}, depth: {depth}, starting_url: {normalized_starting_url}")
                
                # Update job counters
                self.job.total_links += 1
                self.job.save(update_fields=['total_links'])
                
                return link.id
                
        except Exception as e:
            logger.error(f"Error adding link {url}: {e}")
            return None
    
    def add_links(self, links_data, parent_id=None, depth=0, starting_url=None):
        """Add multiple links to the link registry."""
        added_count = 0
        filtered_count = 0
        
        # Filter links before processing
        filtered_links = []
        for link_data in links_data:
            url = link_data.get('url')
            if url and not self.should_filter_url(url):
                filtered_links.append(link_data)
            else:
                filtered_count += 1
        
        logger.info(f"Filtered {filtered_count} out of {len(links_data)} links")
        
        # If we don't have a starting_url but have a parent_id, try to get the parent's starting_url
        if not starting_url and parent_id:
            try:
                parent = Link.objects.get(id=parent_id)
                if parent.starting_url:
                    starting_url = parent.starting_url
                    logger.debug(f"Using parent's starting_url: {starting_url} for {len(filtered_links)} links")
            except Link.DoesNotExist:
                logger.warning(f"Parent link {parent_id} not found when trying to determine starting_url")
        
        # If still no starting_url but at depth 0, these are starting URLs (their own starting_url)
        if not starting_url and depth == 0 and filtered_links:
            first_url = filtered_links[0].get('url')
            if first_url:
                starting_url = first_url
                logger.debug(f"Using link's own URL as starting_url since depth=0: {starting_url}")
        
        with transaction.atomic():
            for link_data in filtered_links:
                url = link_data.get('url')
                link_text = link_data.get('text', '')
                link_type = link_data.get('type', 'page')
                
                # For depth 0 links, use their own URL as starting_url if not specified
                link_starting_url = starting_url
                if depth == 0 and not link_starting_url:
                    link_starting_url = url
                    
                if self.add_link(
                    url=url, 
                    link_type=link_type,
                    parent_id=parent_id,
                    depth=depth,
                    link_text=link_text,
                    starting_url=link_starting_url
                ):
                    added_count += 1
        
        logger.info(f"Added {added_count}/{len(filtered_links)} links at depth {depth}" + 
                  (f" with starting_url {starting_url}" if starting_url else ""))
        return added_count
    
    def mark_as_processed(self, link_id):
        """
        Mark a link as processed.
        
        Args:
            link_id (UUID): UUID of the link to mark
            
        Returns:
            bool: True if successful, False otherwise
        """
        max_retries = 3
        retry_delay = 0.5  # seconds
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Get a fresh copy of the link with locking
                    link = Link.objects.select_for_update().get(id=link_id)
                    link.processed = True
                    link.save()
                    
                    # Update job counter
                    self.job.processed_links += 1
                    self.job.save(update_fields=['processed_links'])
                    
                    return True
            except OperationalError:
                # Handle database lock timeout
                if attempt == max_retries - 1:
                    logger.error(f"Failed to mark link {link_id} as processed after {max_retries} attempts")
                    return False
                logger.warning(f"Database lock when marking link {link_id} as processed, retrying...")
                time.sleep(retry_delay)
            except Link.DoesNotExist:
                logger.warning(f"Link with ID {link_id} not found")
                return False
            except Exception as e:
                logger.error(f"Error marking link {link_id} as processed: {e}")
                return False
                
        return False
    
    def get_unprocessed_links_by_depth(self, depth):
        """
        Get all unprocessed links at a specific depth.
        
        Args:
            depth (int): Depth level to query
            
        Returns:
            QuerySet: Unprocessed links at the specified depth
        """
        return Link.objects.filter(
            job=self.job,
            depth=depth,
            processed=False
        )
    
    def get_links_grouped_by_starting_url(self):
        """
        Group all links by their starting URL origin.
        This uses the starting_url field directly instead of trying to trace 
        parent-child relationships.
        
        Returns:
            dict: Dictionary with starting URLs as keys and lists of related links as values
        """
        try:
            # Simply group links by their starting_url field
            result = {}
            
            # Get all starting URLs (depth 0 links)
            starting_links = Link.objects.filter(job=self.job, depth=0)
            
            # If no starting links were found, log warning and return empty
            if not starting_links:
                logger.warning(f"No starting links (depth 0) found for job {self.job.id}")
                return {}
            
            # Create a mapping of starting URL to list of links
            for starting_link in starting_links:
                result[starting_link.url] = list(
                    Link.objects.filter(job=self.job, starting_url=starting_link.url)
                )
            
            return result
        except Exception as e:
            logger.error(f"Error grouping links by starting URL: {e}")
            return {}
    
    def export_links_to_json(self, links, output_file):
        """
        Export links to a JSON file in a hierarchical structure.
        
        Args:
            links (list): List of Link objects to export
            output_file (str): Path to the output file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build a hierarchical structure
            structure = self._build_hierarchical_structure(links)
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structure, f, indent=4)
            
            return True
        except Exception as e:
            logger.error(f"Error exporting links to JSON: {e}")
            return False
    
    def _build_hierarchical_structure(self, links):
        """
        Build a hierarchical structure of links.
        
        Args:
            links (list): List of Link objects
            
        Returns:
            dict: Hierarchical structure
        """
        # Create a map of link IDs to links
        link_map = {str(link.id): link for link in links}
        
        # Create a map of parent IDs to child links
        children_map = {}
        for link in links:
            if link.parent_id:
                parent_id = str(link.parent_id)
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(link)
        
        # Build the structure recursively
        def build_node(link):
            node = {
                'url': link.url,
                'text': link.link_text,
                'type': link.type if link.type != 'broken' else 'broken',  # Ensure 'broken' type is correctly exported
                'depth': link.depth,
                'processed': link.processed,
                'file_path': link.file_path if link.file_path else None,
                'children': []
            }
            
            # Add children recursively
            if str(link.id) in children_map:
                for child in children_map[str(link.id)]:
                    node['children'].append(build_node(child))
            
            return node
        
        # Start with roots (depth 0)
        roots = [link for link in links if link.depth == 0]
        
        if not roots:
            # If no roots found, include orphaned links
            orphans = []
            for link in links:
                if not link.parent_id or str(link.parent_id) not in link_map:
                    orphans.append(build_node(link))
            return {'roots': orphans}
        
        result = {'roots': [build_node(root) for root in roots]}
        return result

    def should_filter_url(self, url):
        """Check if a URL should be filtered."""
        if not url:
            return False
            
        # Normalize the URL for consistent matching
        normalized_url = self._normalize_url(url)
        
        # Check against cached filters
        for filter_url in self.filters:
            if filter_url in normalized_url:
                return True
                
        return False