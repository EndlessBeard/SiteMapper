# Site_Mapper2 Project Instructions

This document provides instructions for setting up and running the Site_Mapper2 Django project.

## Project Overview

Site_Mapper2 is a Django-based web crawler and site mapping application. The project follows a standard Django structure with the following components:

- `site_mapper`: Main application that handles site crawling, document parsing, and content extraction
- `web_django`: Core Django project settings and configuration
- `media`: Storage directory for crawled content and files

## Setup Instructions

### Prerequisites

- Python 3.x
- Virtual environment tool (venv, conda, etc.)

### Environment Setup

The project uses a virtual environment to manage dependencies. Always activate the virtual environment before running any commands:

```bash
# Navigate to the project directory
cd /Users/rachelhoover/Desktop/Dave\ Projects/Site_Mapper2/SiteMapper/

# Activate the virtual environment
source venv/bin/activate
```

If the virtual environment doesn't exist yet, create it:

```bash
# Create a new virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### Database Setup

If setting up for the first time, run migrations:

```bash
python manage.py migrate
```

Create a superuser to access the admin interface:

```bash
python manage.py createsuperuser
```

## Running the Server

Always make sure the virtual environment is activated before starting the server:

```bash
# Navigate to the project directory
cd /Users/rachelhoover/Desktop/Dave\ Projects/Site_Mapper2/SiteMapper/

# Activate the virtual environment
source venv/bin/activate

# Run the development server
python manage.py runserver
```

The application will be accessible at http://127.0.0.1:8000/

## Restarting the Server

When code changes are made, especially to model definitions or core functionality, it's important to properly restart the server to ensure all changes are loaded. Follow these steps:

### Method 1: Standard Restart (Preferred)

```bash
# Stop the current server with Ctrl+C
# Then restart with:
cd /Users/rachelhoover/Desktop/Dave\ Projects/Site_Mapper2/SiteMapper/
source venv/bin/activate
python3 manage.py runserver
```

### Method 2: Force Stop and Restart

If the server isn't responding to Ctrl+C or you need to ensure all Django processes are stopped:

```bash
# Find and stop all Django server processes
ps aux | grep "python.*runserver" | grep -v grep | awk '{print $2}' | xargs kill -9

# Then start a fresh server:
cd /Users/rachelhoover/Desktop/Dave\ Projects/Site_Mapper2/SiteMapper/
source venv/bin/activate
python manage.py runserver
```

### Running on a Different Port

To run the server on a non-default port (e.g., if port 8000 is already in use):

```bash
cd /Users/rachelhoover/Desktop/Dave\ Projects/Site_Mapper2/SiteMapper/
source venv/bin/activate
python manage.py runserver 8080  # Or any other port number
```

The application will then be accessible at http://127.0.0.1:8080/ (or whichever port you specified).

## Project Structure

- `site_mapper/core/`: Contains the core crawler functionality
  - `crawler.py`: Web crawling implementation
  - `document_parser.py`: Parses different document types
  - `link_extractor.py`: Extracts links from web pages
  - `site_processor.py`: Processes entire sites for mapping

- `site_mapper/templates/`: Contains HTML templates for the UI
- `site_mapper/static/`: Contains static assets (CSS, JS, images)
- `media/site_mapper/`: Contains output data from crawling jobs

## Common Issues

- **"Couldn't import Django"**: This typically means the virtual environment is not activated. Make sure to run `source venv/bin/activate` before running any Django commands.

- **Path Issues**: Ensure you're in the correct directory when running commands (`/Users/rachelhoover/Desktop/Dave Projects/Site_Mapper2/SiteMapper/`).

- **Database Errors**: If you encounter database errors after making model changes, try running migrations:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```

## Development Guidelines

- Add new functionality to the appropriate modules in the `site_mapper/core/` directory
- Use Django's template system for UI components
- Store media files in the appropriate subdirectories of `media/site_mapper/`
- Keep the virtual environment active during development