"""
Website Crawler module for Site_Mapper2.
This module handles fetching web pages and extracting their content.
"""
import logging
import os, uuid
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class WebCrawler:
    """
    Handles crawling websites and extracting content.
    Uses Selenium for JavaScript-enabled sites and exposes hidden elements.
    """
    
    def __init__(self, headless=True, timeout=30):
        """
        Initialize the WebCrawler with browser options.
        
        Args:
            headless (bool): Whether to run the browser in headless mode
            timeout (int): Maximum time to wait for page load in seconds
        """
        self.timeout = timeout
        self.driver = None
        self.headless = headless
        
    def _initialize_driver(self):
        """Initialize the Selenium WebDriver if not already done."""
        if self.driver is None:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                
                # Setup Chrome options
                chrome_options = Options()
                if self.headless:
                    chrome_options.add_argument('--headless')
                    
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                
                # Use webdriver-manager to automatically download correct ChromeDriver version
                service = Service(ChromeDriverManager().install())
                
                # Initialize the driver with the service
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(self.timeout)
                
                logger.info("WebDriver initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing WebDriver: {e}")
                raise
    
    def close(self):
        """Close the WebDriver if it's open."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def fetch_page(self, url):
        """
        Fetch a webpage and return its content after processing JavaScript.
        
        Args:
            url (str): URL of the page to fetch
            
        Returns:
            tuple: (page_content, page_title, soup_object)
        """
        try:
            self._initialize_driver()
            
            # Verify driver is properly initialized before continuing
            if not self.driver:
                logger.error(f"WebDriver not initialized when fetching {url}")
                return None, None, None
                
            logger.info(f"Fetching page: {url}")
            
            # Navigate to the URL
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try to expand interactive elements
            self._expand_interactive_elements()
            
            # Get page content and title
            page_content = self.driver.page_source
            page_title = self.driver.title
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Log success
            logger.info(f"Successfully fetched page: {url} (title: {page_title})")
            
            return page_content, page_title, soup
        except TimeoutException:
            logger.error(f"Timeout while loading {url}")
            return None, None, None
        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {e}")
            return None, None, None
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None, None, None
    
    def _expand_interactive_elements(self):
        """Expand hidden menus, dropdowns, and other interactive elements."""
        try:
            # Click on menu buttons
            menu_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                                                   ".menu-button, .navbar-toggler, button[aria-expanded='false']")
            
            for element in menu_elements:
                if element.is_displayed() and element.is_enabled():
                    try:
                        element.click()
                        time.sleep(1)  # Give time for animation
                    except Exception as e:
                        logger.debug(f"Could not click menu element: {e}")
            
            # Expand accordions and collapsible content
            expandable_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                         ".accordion-button, .collapse-toggle, [data-bs-toggle='collapse']")
            
            for element in expandable_elements:
                if element.is_displayed() and element.is_enabled():
                    try:
                        element.click()
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Could not expand element: {e}")
                        
        except Exception as e:
            logger.warning(f"Error expanding interactive elements: {e}")
    
    def download_file(self, url, destination_dir, filename=None):
        """
        Download a file from a URL.
        
        Args:
            url (str): URL to download
            destination_dir (str): Directory to save the file
            filename (str, optional): Filename to use
            
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Create a session that follows redirects but keeps track of them
            session = requests.Session()
            
            # Get the file with redirect tracking
            response = session.get(url, allow_redirects=True, timeout=30)
            
            # Check if we got redirected to a different content type
            final_url = response.url
            if final_url != url:
                logger.info(f"URL redirected: {url} → {final_url}")
                
            # Check the content type
            content_type = response.headers.get('Content-Type', '')
            
            # Verify content type matches expected file type based on URL/filename
            expected_type = self._get_expected_content_type(url, filename)
            if expected_type and expected_type not in content_type:
                logger.warning(f"Content type mismatch: Expected {expected_type}, got {content_type}")
                return None
                
            if response.status_code != 200:
                logger.error(f"Failed to download {url}: HTTP {response.status_code}")
                return None
                
            # Generate filename if not provided
            if not filename:
                filename = os.path.basename(urlparse(url).path)
                if not filename:
                    filename = f"file_{uuid.uuid4().hex}"
                    
                # Add extension based on content type if needed
                if '.' not in filename:
                    ext = self._get_extension_from_content_type(content_type)
                    if ext:
                        filename += ext
                        
            # Save the file
            file_path = os.path.join(destination_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
            return file_path
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
            
    def _get_expected_content_type(self, url, filename):
        """Determine expected content type based on URL or filename."""
        if url.lower().endswith('.pdf') or (filename and filename.lower().endswith('.pdf')):
            return 'application/pdf'
        elif any(url.lower().endswith(ext) or (filename and filename.lower().endswith(ext)) 
                for ext in ['.doc', '.docx']):
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml'
        elif any(url.lower().endswith(ext) or (filename and filename.lower().endswith(ext)) 
                for ext in ['.xls', '.xlsx']):
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml'
        return None
        
    def _get_extension_from_content_type(self, content_type):
        """Get file extension from content type."""
        if 'application/pdf' in content_type:
            return '.pdf'
        elif 'application/vnd.openxmlformats-officedocument.wordprocessingml' in content_type:
            return '.docx'
        elif 'application/vnd.openxmlformats-officedocument.spreadsheetml' in content_type:
            return '.xlsx'
        return ''