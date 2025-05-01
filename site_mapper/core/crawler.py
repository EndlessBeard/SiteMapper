"""
Website Crawler module for Site_Mapper2.
This module handles fetching web pages and extracting their content.
"""
import logging
import os
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
                options = Options()
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                self.driver = webdriver.Chrome(options=options)
                self.driver.set_page_load_timeout(self.timeout)
            except WebDriverException as e:
                logger.error(f"Failed to initialize WebDriver: {e}")
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
            
            logger.info(f"Fetching page: {url}")
            self.driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Let JavaScript execute
            time.sleep(3)
            
            # Expand hidden menus and elements
            self._expand_interactive_elements()
            
            page_source = self.driver.page_source
            page_title = self.driver.title
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            return page_source, page_title, soup
            
        except TimeoutException:
            logger.warning(f"Timeout while loading {url}")
            return None, None, None
        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {e}")
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
            url (str): URL of the file to download
            destination_dir (str): Directory to save the file
            filename (str, optional): Name of the file
            
        Returns:
            str: Path to the downloaded file or None if download failed
        """
        try:
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
                
            if not filename:
                filename = url.split('/')[-1].split('?')[0]  # Extract filename from URL
                
            file_path = os.path.join(destination_dir, filename)
            
            response = requests.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded {url} to {file_path}")
            return file_path
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return None