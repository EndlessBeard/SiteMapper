"""
Link Extractor module for Site_Mapper2.
This module identifies and classifies links from HTML content.
"""
import logging
import re
import urllib.parse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class LinkExtractor:
    """
    Identifies and classifies links from HTML content.
    Separates document links, content links, and navigation links.
    """
    
    # Extensions for document types we're interested in
    DOCUMENT_EXTENSIONS = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'docx',
        'xlsx': 'xlsx',
        'xls': 'xlsx',
        'pptx': 'pptx',
        'ppt': 'pptx',
    }
    
    # Elements that typically contain navigation elements
    NAVIGATION_SELECTORS = [
        'nav', 'header', 'footer', '.nav', '.navbar', '.menu', '.navigation',
        '.sidebar', '#sidebar', '#nav', '#menu', '.topnav', '.main-nav',
        '[role="navigation"]', '.quick-links', '.quicklinks'
    ]
    
    # Elements that typically contain announcements
    ANNOUNCEMENT_SELECTORS = [
        '.announcement', '.announcements', '.news', '.alert', '.update',
        '.notice', '.post', '.article', '.announcement-banner'
    ]
    
    # Regular expression pattern to match email addresses
    EMAIL_PATTERN = re.compile(r'^(?:mailto:)?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Phone number patterns
    PHONE_PATTERN = re.compile(r'^(?:tel:)?(?:\+?\d[\d\s\(\)-]*){5,}$')

    def __init__(self, base_url):
        """
        Initialize the LinkExtractor.
        
        Args:
            base_url (str): The base URL for resolving relative links
        """
        self.base_url = base_url
    
    def extract_links(self, soup):
        """
        Extract links from a BeautifulSoup object and classify them.
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            
        Returns:
            dict: Classification of links as documents, content, and navigation
        """
        if not soup:
            return {'documents': [], 'content': [], 'navigation': []}
            
        all_links = soup.find_all('a', href=True)
        
        documents = []
        content = []
        navigation = []
        
        navigation_elements = self._find_navigation_elements(soup)
        announcement_elements = self._find_announcement_elements(soup)
        
        for link in all_links:
            url = self._normalize_url(link['href'])
            if not url:
                continue
                
            # Check for email links and skip them
            if self._is_email_link(url):
                logger.debug(f"Skipping email link: {url}")
                continue
            
            # Check for phone links and skip them
            if self._is_phone_link(url):
                logger.debug(f"Skipping phone link: {url}")
                continue
                
            link_info = {
                'url': url,
                'text': link.get_text(strip=True) or url,
                'type': self._determine_link_type(url)
            }
            
            # Check if it's a document link
            if link_info['type'] in self.DOCUMENT_EXTENSIONS.values():
                documents.append(link_info)
                continue
                
            # Check if it's in a navigation element
            if any(link in element.descendants for element in navigation_elements):
                navigation.append(link_info)
                continue
                
            # Check if it's in an announcement element - SKIP THESE
            if any(link in element.descendants for element in announcement_elements):
                # Skip announcement links instead of adding them
                logger.debug(f"Skipping announcement link: {url}")
                continue
                
            # Otherwise it's regular content
            content.append(link_info)
            
        logger.info(f"Extracted {len(documents)} document links, {len(content)} content links, "
                   f"and {len(navigation)} navigation links")
        
        return {
            'documents': documents,
            'content': content,
            'navigation': navigation
        }
    
    def _find_navigation_elements(self, soup):
        """Find elements that are likely navigation containers."""
        navigation_elements = []
        
        for selector in self.NAVIGATION_SELECTORS:
            navigation_elements.extend(soup.select(selector))
            
        return navigation_elements
    
    def _find_announcement_elements(self, soup):
        """Find elements that are likely announcement containers."""
        announcement_elements = []
        
        for selector in self.ANNOUNCEMENT_SELECTORS:
            announcement_elements.extend(soup.select(selector))
            
        return announcement_elements
    
    def _is_email_link(self, url):
        """
        Check if the URL is an email link (mailto: or contains an email pattern).
        
        Args:
            url (str): URL to check
            
        Returns:
            bool: True if it's an email link, False otherwise
        """
        if not url:
            return False
            
        # Check for mailto: protocol
        if url.startswith('mailto:'):
            return True
            
        # Check for email pattern using regex
        return bool(self.EMAIL_PATTERN.match(url))
    
    def _is_phone_link(self, url):
        """
        Check if the URL is a phone link (tel: or contains a phone number pattern).
        
        Args:
            url (str): URL to check
            
        Returns:
            bool: True if it's a phone link, False otherwise
        """
        if not url:
            return False
            
        # Check for tel: protocol
        if url.startswith('tel:'):
            return True
        
        # Check for phone pattern using regex (simple implementation)
        return bool(self.PHONE_PATTERN.match(url))

    def _normalize_url(self, url):
        """
        Normalize a URL by resolving relative URLs and removing fragments.
        
        Args:
            url (str): URL to normalize
            
        Returns:
            str: Normalized URL
        """
        if not url or url.startswith('#') or url.startswith('javascript:'):
            return None
            
        # Parse the URL and join with base if relative
        parsed_url = urllib.parse.urlparse(url)
        
        if not parsed_url.netloc:
            absolute_url = urllib.parse.urljoin(self.base_url, url)
        else:
            absolute_url = url
            
        # Remove fragments
        parsed_absolute = urllib.parse.urlparse(absolute_url)
        clean_url = urllib.parse.urlunparse((
            parsed_absolute.scheme,
            parsed_absolute.netloc,
            parsed_absolute.path,
            parsed_absolute.params,
            parsed_absolute.query,
            ''  # Remove fragment
        ))
        
        return clean_url
    
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
        extension = url.split('.')[-1].lower().split('?')[0]
        
        return self.DOCUMENT_EXTENSIONS.get(extension, 'page')