# Site Mapper

Site Mapper is a comprehensive web crawling and site mapping tool built with Django. It helps you explore and document website structures by crawling web pages, extracting links, and analyzing documents like PDFs and Office files.

## Features

- **Website Crawling**: Automated multi-level depth website exploration
- **Document Analysis**: Extract links from PDF, Word, and Excel documents
- **Interactive Dashboard**: Monitor jobs and view mapping progress in real-time
- **Export Options**: Download results as JSON or Word document
- **Configurable Settings**: Set crawl depth, starting URLs, and more

The code in this repo follows Python style guidelines as outlined in [PEP 8](https://peps.python.org/pep-0008/).

## Running the Application

To successfully run this application, we recommend the following VS Code extensions:
- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy)
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) 

- Open the project folder in VS Code (**File** > **Open Folder...**)
- Create a Python virtual environment using the **Python: Create Environment** command found in the Command Palette (**View > Command Palette**). Ensure you install dependencies found in the `requirements.txt` file
- Ensure your newly created environment is selected using the **Python: Select Interpreter** command found in the Command Palette
- Create and initialize the database by running `python manage.py migrate` in an activated terminal
- Run the app using the Run and Debug view or by pressing `F5`
- Access the application at http://127.0.0.1:8000/ in your web browser
- Run tests by running `python manage.py test` in an activated terminal

## Usage

1. Navigate to the dashboard and create a new mapping job
2. Enter a job name and starting URL(s)
3. Set the maximum crawl depth
4. Start the job and monitor progress
5. Once completed, download results as JSON or Word document

## Issues

-   Improve link detection using content header types
-   Removed click depth step through
-   DJANGO related CSS errors from VSCODE
-   Progress Bars