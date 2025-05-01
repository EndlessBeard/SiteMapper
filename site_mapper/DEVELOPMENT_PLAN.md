# Site_Mapper2: Website Mapping Tool Development Plan

## Overview
Site_Mapper2 is a tool for mapping websites and analyzing links across pages and documents. It focuses on thorough page analysis, document link identification, and comprehensive link cataloging.

## Architecture

### Modular Design
The application is structured into independent modules, each responsible for a specific functionality:

1. **Core Components**:
   - `crawler.py`: Handles webpage fetching and content extraction
   - `link_extractor.py`: Identifies and classifies links from HTML content
   - `document_parser.py`: Extracts links from various document types
   - `link_manager.py`: Manages the link registry and prevents duplicates

2. **Document Handlers**:
   - `pdf_handler.py`: Extracts text and links from PDF files
   - `office_handler.py`: Processes Microsoft Office documents (.docx, .xlsx)

3. **UI Components**:
   - `views.py`: Defines Django views for the web interface
   - `templates/`: Contains HTML templates for the UI
   - `static/`: CSS, JavaScript, and other static assets

## Data Model

### Link Data Structure
```python
class Link:
    uuid: str           # Unique identifier
    url: str            # Full URL
    link_text: str      # Anchor text or description
    type: str           # Type of link (internal, external, document)
    file_path: str      # Path to saved file (if applicable)
    children: List[str] # UUIDs of child links
```

## Processing Flow

### Phase 1: Initial Page Parsing
1. Load each target URL
2. Use Selenium to interact with the page:
   - Open hidden menus
   - Expand collapsible elements
3. Extract all links:
   - Document links (.pdf, .xlsx, .docx)
   - Content links (excluding navigation)
4. Save links to master list with UUID assignment

### Phase 2: Document Analysis
1. Process all links from Phase 1
2. For document links:
   - Download documents
   - Extract text and links using appropriate parser
   - Add new links to master list (avoiding duplicates)

## Technical Implementation

### Crawler Module
- Uses Selenium WebDriver for JavaScript-enabled sites
- BeautifulSoup for HTML parsing
- Custom logic to identify and interact with navigation elements

### Document Parsing
- PDF: PyPDF2 or pdfminer.six for text extraction
- Office: python-docx for Word, openpyxl for Excel

### User Interface
- Django-based web interface
- Real-time processing status updates
- Configuration options for output file naming

## Output Format
```json
[
  {
    "uuid": "12345678-90ab-cdef-1234-567890abcdef",
    "url": "https://example.com/page1",
    "link_text": "Example Page",
    "type": "page",
    "file_path": "output/page1.html",
    "children": [
      "98765432-10fe-dcba-9876-543210fedcba"
    ]
  }
]
```

## Dependencies
- Django: Web framework
- Selenium: Browser automation
- BeautifulSoup4: HTML parsing
- PyPDF2/pdfminer.six: PDF processing
- python-docx: Word document processing
- openpyxl: Excel document processing
- Requests: HTTP client