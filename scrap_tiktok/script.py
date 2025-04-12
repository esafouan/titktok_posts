from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os
import logging
import json
import hashlib
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('data', exist_ok=True)
os.makedirs('images', exist_ok=True)

def setup_driver():
    """Set up and return a configured Chrome driver that connects to Selenium Grid"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    # Get Selenium Hub URL from environment or use default
    selenium_hub_url = os.environ.get('SELENIUM_HUB_URL', 'http://selenium-hub:4444/wd/hub')
    
    try:
        # Use Remote WebDriver to connect to Selenium Grid
        driver = webdriver.Remote(
            command_executor=selenium_hub_url,
            options=chrome_options
        )
        logger.info(f"WebDriver initialized successfully, connected to Selenium Grid at {selenium_hub_url}")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {e}")
        raise


def extract_post_data(driver, post_url):
    """Extract and save complete HTML from a Facebook post for later processing"""
    try:
        driver.get(post_url)
        post_id = generate_post_id(post_url)
        # Wait for content to load with dynamic detection
        time.sleep(4)
        # Save the complete page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

    
        description_spans = soup.find_all('picture')
        
        with open('./data/tiktok.html', 'w') as f:
            f.write(str(description_spans))
            
        
        # if description_spans:
        #     full_description = ' '.join([' '.join([div.get_text(strip=True) for div in span.find_all('div', dir='auto')]) for span in description_spans])
        # else:
        #     description_divs = soup.find_all('div', {'dir': 'auto', 'style': 'text-align: start;'})
        #     full_description = ' '.join([div.get_text(strip=True) for div in description_divs])
        
        # # Extract image
        # img_tag = soup.find('img', class_='x168nmei x13lgxp2 x5pf9jr xo71vjh x1ey2m1c xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3 xl1xv1r')
        # image_url = img_tag['src'] if img_tag else None

        return {
            "url": post_url,
            "id": post_id,
            # "image_url": image_url,
            # "description": full_description,
            "success": True
        }      
    except Exception as e:
        logger.error(f"Failed to extract and save post data: {e}", exc_info=True)
        return {
            "url": post_url,
            "id": generate_post_id(post_url),
            "success": False,
            "error": str(e)
        }

def generate_post_id(url):
    """Generate a unique ID for a post based on its URL"""
    return hashlib.md5(url.encode()).hexdigest()

def save_data_to_json(data_list, filename="data/facebook_posts.json"):
    """Save scraped data to a JSON file"""
    try:
        # Check if file exists and load existing data
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []
        
        # Create a dictionary with post_id as key for easy lookup
        data_dict = {item['id']: item for item in existing_data}
        
        # Update with new data
        for item in data_list:
            data_dict[item['id']] = item
        
        # Convert back to list
        updated_data = list(data_dict.values())
        
        # Save updated data
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to JSON: {e}")
        return False

def load_existing_data(json_filename="data/facebook_posts.json"):
    """Load existing data from JSON file"""
    try:
        if os.path.exists(json_filename):
            with open(json_filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} existing posts from {json_filename}")
            return data
        else:
            logger.info(f"No existing data found at {json_filename}")
            return []
    except Exception as e:
        logger.error(f"Error loading existing data: {e}")
        return []

def process_urls_from_file(filename="urls.txt"):
    """Process URLs from a text file"""
    try:
        if not os.path.exists(filename):
            logger.error(f"URL file {filename} not found")
            return None
            
        with open(filename, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
            
        logger.info(f"Loaded {len(urls)} URLs from {filename}")
        return urls
    except Exception as e:
        logger.error(f"Error loading URLs from file: {e}")
        return None

def main():
    """Main function to run the Facebook batch scraper"""
    urls = process_urls_from_file("urls.txt")
    existing_data = load_existing_data()
    existing_ids = {item['id'] for item in existing_data}
    
    # Initialize driver
    driver = None
    results = []
    
    try:
        driver = setup_driver()
        # Process each URL
        for url in urls:
            post_id = generate_post_id(url)
            
            # Skip already processed URLs
            if post_id in existing_ids:
                logger.info(f"Skipping already processed URL: {url}")
                continue
                
            # Extract post data
            post_data = extract_post_data(driver, url)
            
            # Add to results
            if post_data:
                logger.info(f"-------------------------------: {post_data}")
                results.append(post_data)
                logger.info(f"Successfully processed URL: {url}")
            
            # Avoid rate limiting
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
    finally:
        # Close the browser
        if driver:
            driver.quit()
            logger.info("Browser closed")
    
    # Save results if we have any
    if results:
        # Save to JSON
        save_data_to_json(results)
        
        
        logger.info(f"Successfully processed {len(results)} URLs")
    else:
        logger.info("No new data to save")

if __name__ == "__main__":
    main()