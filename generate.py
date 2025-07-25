import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import json # <-- ADDED for JSON functionality

# --- THIS IS YOUR ORIGINAL, UNCHANGED SCRAPING FUNCTION ---
def get_tomorrows_papers_front_pages():
    """Scrape front page images from Tomorrow's Papers Today"""
    url = "https://www.tomorrowspapers.co.uk/"
    
    # Headers to avoid 403 blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        items = []
        
        # Look for images in the front pages section
        # Try different selectors that might contain the front page images
        img_selectors = [
            "img[src*='front']",  # Images with 'front' in src
            "img[alt*='front']",  # Images with 'front' in alt text
            "img[alt*='newspaper']",  # Images with 'newspaper' in alt
            ".front-page img",  # Images in elements with front-page class
            "article img",  # Images in article elements
            "main img",  # Images in main content
            "img"  # Fallback to all images
        ]
        
        for selector in img_selectors:
            images = soup.select(selector)
            for img in images:
                src = img.get("src") or img.get("data-src")
                if not src:
                    continue
                    
                # Convert relative URLs to absolute
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://www.tomorrowspapers.co.uk" + src
                elif not src.startswith("http"):
                    continue
                
                # Skip very small images (likely logos/icons)
                width = img.get("width")
                height = img.get("height")
                if width and height:
                    try:
                        if int(width) < 100 or int(height) < 100:
                            continue
                    except ValueError:
                        pass
                
                alt = img.get("alt", "")
                
                # If no alt text, extract newspaper name from filename
                if not alt or alt.strip() == "":
                    # Extract filename from URL and clean it up
                    filename = src.split('/')[-1].split('.')[0]  # Get filename without extension
                    # Remove trailing numbers like "-1", "-8" etc first
                    filename = re.sub(r'-\d+$', '', filename)
                    # Then replace hyphens with spaces
                    alt = filename.replace('-', ' ').strip()
                    if not alt:
                        alt = "Newspaper Front Page"
                
                # Skip images that are clearly not front pages
                if any(skip_word in src.lower() for skip_word in ['logo', 'icon', 'avatar', 'profile']):
                    continue
                if any(skip_word in alt.lower() for skip_word in ['logo', 'icon', 'avatar', 'profile']):
                    continue
                
                # Avoid duplicates
                if not any(item[1] == src for item in items):
                    items.append((alt, src))

                if len(items) >= 10:  # Get up to 10 images
                    break
            
            if items:  # If we found images with this selector, stop trying others
                break
        
        return items
        
    except requests.RequestException as e:
        print(f"Error fetching Newsworks page: {e}")
        return []

# --- THIS IS YOUR ORIGINAL, UNCHANGED RSS FUNCTION ---
def generate_rss(items, source_url):
    """Generate RSS feed from front page items"""
    rss_items = ""
    for title, img_url in items:
        # Escape XML special characters in title
        title = title.replace("&", "&").replace("<", "<").replace(">", ">")
        
        rss_items += f"""
        <item>
          <title>{title}</title>
          <link>{img_url}</link>
          <description><![CDATA[<img src="{img_url}" alt="{title}" />]]></description>
          <guid>{img_url}</guid>
          <pubDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
        </item>
        """

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>UK Newspaper Front Pages - Tomorrow's Papers Today</title>
    <link>{source_url}</link>
    <description>Daily UK newspaper front pages from Tomorrow's Papers Today</description>
    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <language>en-GB</language>
    {rss_items}
  </channel>
</rss>
"""
    return rss_feed

# --- THIS IS THE NEW FUNCTION TO GENERATE JSON ---
def generate_json(items, source_url, rss_feed_url):
    """Generate JSON feed from front page items in the specified format."""
    pub_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    output_dict = {
        "status": "ok",
        "feed": {
            "url": rss_feed_url,
            "title": "UK Newspaper Front Pages - Tomorrow's Papers Today",
            "link": source_url,
            "author": "",
            "description": "Daily UK newspaper front pages from Tomorrow's Papers Today",
            "image": ""
        },
        "items": []
    }

    for title, img_url in items:
        image_html = f'<img src="{img_url}" alt="{title}">'
        
        item_dict = {
            "title": title,
            "pubDate": pub_date_str,
            "link": img_url,
            "guid": img_url,
            "author": "",
            "thumbnail": "",
            "description": image_html,
            "content": image_html,
            "enclosure": {},
            "categories": []
        }
        output_dict["items"].append(item_dict)

    return json.dumps(output_dict, indent=2)

# --- THIS IS YOUR MAIN FUNCTION, MODIFIED TO ADD THE JSON STEPS ---
def main():
    """Main function to scrape and generate RSS and JSON"""
    source_url = "https://www.tomorrowspapers.co.uk/"
    rss_feed_url = "https://lak7474.github.io/frontpages-app-repo/rss.xml"
    
    print("Scraping front pages from Tomorrow's Papers Today...")
    items = get_tomorrows_papers_front_pages()
    
    if not items:
        print("No front page images found.")
        return
    
    print(f"Found {len(items)} front page images:")
    for title, url in items:
        print(f"  - {title}")
    
    # Original RSS generation
    rss_xml = generate_rss(items, source_url)
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(rss_xml)
    print("RSS feed generated as 'rss.xml'")

    # Added JSON generation
    json_output = generate_json(items, source_url, rss_feed_url)
    with open("frontpages.json", "w", encoding="utf-8") as f:
        f.write(json_output)
    print("JSON feed generated as 'frontpages.json'")

if __name__ == "__main__":
    main()
