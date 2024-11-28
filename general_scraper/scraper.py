import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_promotions(url):
    """
    Scrape promotions from the SBB website.

    Args:
        url (str): The URL of the SBB promotions page.

    Returns:
        pd.DataFrame: A DataFrame containing promotion details.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers)

        # exception handling?
        response.raise_for_status()  # Raise an error for bad status codes

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Adjust selectors based on the actual SBB page structure
        # promotions = soup.find_all('li', class_='mod_lh_teaser_homepage_teasers_list_item')
        promotions = soup.find_all('div', class_='mod_lh_teaser')  # Update the class as needed
        
        data = []
        # for promo in promotions:
        #     a_tag = promo.find('a')  # Find the first <a> tag inside the <li>
        #     if a_tag:
        #         print(a_tag.text)  # Print the text content of the <a> tag
        #         print("================================\n")
        #     else:
        #         print("No link found in this <li>")
        
        # Find the <a> tag
        a_tag = soup.find('a', class_='mod_lh_teaser_link')

        # Extract useful information:
        if a_tag:
            href = a_tag['href']
            headline = a_tag['data-sit-teaser-headline']
            label = a_tag['data-sit-teaser-label']
            offer = a_tag.find('div', class_='mod_white_panel_tag').text.strip()
            description = a_tag.find('div', class_='mod_lh_teaser_lead').text.strip()

            print("Link:", href)
            print("Headline:", headline)
            print("Label:", label)
            print("Offer:", offer)
            print("Description:", description)
        else:
            print("No <a> tag found.")

        df = pd.DataFrame(data)
        
        return df
    
    except requests.exceptions.RequestException as e:
        print("error = ", e)
        return pd.DataFrame()  # Return empty DataFrame on failure

# For testing the scraper
if __name__ == "__main__":
    test_url = "https://www.sbb.ch/en/leisure-holidays/discover-excursion-ideas.html"  # Replace with actual promotions URL
    promotions_df = scrape_promotions(test_url)
    
    if not promotions_df.empty:
        print("Successfully scraped promotions")
        print(promotions_df)
        # promotions_df.to_csv("sbb_promotions.csv", index=False)
        
    else:
        print("Failed to scrape promotions")