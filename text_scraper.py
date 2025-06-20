# text_scraper.py
import os  # For file path operations
import re  # For regex pattern matching
import time  # For adding delays to let web pages load
from selenium import webdriver  # Controls the browser
from selenium.webdriver.chrome.service import Service  # Manages ChromeDriver execution
from selenium.webdriver.chrome.options import Options  # Sets options for headless browser operation
from selenium.webdriver.common.by import By  # Provides methods to locate elements
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException  # Exception handling for dynamic pages

# Regex to match lines made entirely of decorative characters (e.g., ===, ---)
DECORATIVE_PATTERNS = [r'^\s*[=~\-*_\.]{3,}\s*$']
# Precompiled regex for performance
compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in DECORATIVE_PATTERNS]
# Regex to identify chapter titles like "Book 1 and Chapter 2"
chapter_header_pattern = re.compile(r"^Book (\d+) and Chapter (\d+)")

def clean_text(text):
    cleaned_lines = []  # Will store the cleaned version of the text
    for line in text.splitlines():  # Iterate through each line of the input text
        stripped_line = line.strip()  # Trim whitespace from both ends
        # Skip lines that match decorative patterns
        if any(pattern.match(stripped_line) for pattern in compiled_patterns):
            continue
        # Replace shorthand formats like B3C12 with "Book 3 and Chapter 12"
        line = re.sub(r'\bB(\d+)(C(\d+))?\b', lambda m: f"Book {m.group(1)}" + (f" and Chapter {m.group(3)}" if m.group(3) else ""), line)
        cleaned_lines.append(line)  # Keep the cleaned line
    return "\n".join(cleaned_lines)  # Return full cleaned text as one string

def extract_chapters_and_titles(text):
    ordered_titles = []  # List of chapter titles
    ordered_chapters = []  # List of chapter text blocks
    current = []  # Temporarily holds lines for the current chapter
    current_title = None  # Will store the current chapter's title

    for line in text.splitlines():
        match = chapter_header_pattern.match(line)  # Try to match chapter header
        if match:
            current_title = f"Book_{match.group(1)}_Chapter_{match.group(2)}"  # Construct title from match
            if current:  # If a chapter was being collected
                ordered_chapters.append("\n".join(current))  # Store the previous chapter's content
                ordered_titles.append(current_title or "segment")  # Store title or use default
                current = []  # Reset for next chapter
        current.append(line)  # Add line to current chapter content

    if current:  # Catch last chapter after loop ends
        ordered_chapters.append("\n".join(current))
        ordered_titles.append(current_title or "segment")

    return ordered_titles, ordered_chapters  # Return lists of titles and chapters

def download_book(url, title_selector, content_selector, next_button_selector):
    options = Options()  # Chrome options for browser behavior
    options.add_argument("--headless")  # Run browser invisibly
    options.add_argument("--disable-gpu")  # Disable GPU for headless mode
    options.add_argument("--window-size=1920,1080")  # Set browser window size

    service = Service()  # Create a ChromeDriver service instance
    driver = webdriver.Chrome(service=service, options=options)  # Launch Chrome browser
    driver.get(url)  # Open the given URL
    time.sleep(1)  # Wait for the page to fully load

    os.makedirs("book", exist_ok=True)  # Create "book" folder if it doesn't exist
    book_path = os.path.join("book", "book.txt")  # Define the path for saving scraped content

    with open(book_path, "w", encoding="utf-8") as f:  # Open output file for writing
        while True:
            try:
                # Locate and extract the chapter title element using the selector
                title_elem = driver.find_element(By.CSS_SELECTOR, title_selector)
                title = title_elem.text  # Get the text content of the title

                # Locate and extract the main content of the chapter
                content_elem = driver.find_element(By.CSS_SELECTOR, content_selector)
                content = content_elem.text  # Get the text of the content

                # Format and normalize the title to standard form
                formatted_title = re.sub(r'\bB(\d+)(C(\d+))?\b', lambda m: f"Book {m.group(1)}" + (f" and Chapter {m.group(3)}" if m.group(3) else ""), title)
                full_text = f"{formatted_title}\n\n{content}"  # Combine title and content
                cleaned_text = clean_text(full_text)  # Clean the combined text

                # Write cleaned chapter to file with divider line
                f.write(cleaned_text + "\n\n" + "="*80 + "\n\n")

                # Click the next chapter button to proceed
                next_button = driver.find_element(By.CSS_SELECTOR, next_button_selector)
                driver.execute_script("arguments[0].click();", next_button)  # Use JS click in case normal click fails
                time.sleep(1)  # Short pause to allow page transition

            except (NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException):
                break  # Exit loop when there's no more content or button is unavailable

    driver.quit()  # Close the browser session when done
