import time
import csv
import requests
import os
import re
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Maximum number of pages to scrape
MAX_PAGES = 0  # Set to 0 for no limit, or specify a number

# Rate limits: 2 requests per second
RATE_LIMIT = 2
RATE_PERIOD = 1

# User-Agent header
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Headers with the User-Agent
headers = {"User-Agent": USER_AGENT}


# Rate limit decorator
@sleep_and_retry
@limits(calls=RATE_LIMIT, period=RATE_PERIOD)
# Function to fetch url
def fetch_url(url):
    return requests.get(url, headers=headers)

# Function to extract data about all therapists in a specific province


def scrape_city_data(province, city, datetimestring):
    city_url = f"https://www.psychologytoday.com/ca/therapists/{province}/{city}?category=in-person"
    response = fetch_url(city_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Get the total number of pages for the province
        num_pages = get_num_pages(city_url)
        print(f"Number of pages to scrape for {city}: {num_pages}")

        # Iterate over each page and scrape therapist data
        for page_num in range(1, num_pages + 1):
            therapists_data = []
            page_url = f"{city_url}&page={page_num}"
            response = fetch_url(page_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                therapists_data.extend(scrape_page_data(soup, province))
                save_to_csv(therapists_data, city, datetimestring)
                print(f"Page {page_num} scraped and added to file {city}.csv")
            else:
                print(f"Failed to fetch page: {page_url}")

        return
    else:
        print(f"Failed to fetch city data: {city_url}")
        return

# Function to find the number of pages of a specific category


def get_num_pages(url):
    num_pages = 0
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the div tag for pagination
        pagination_div = soup.find(
            'div', class_='results-pagination-container')
        if pagination_div:
            pages = pagination_div.find_all('a')
            highest_page_number = 0
            new_highest_page_number = True

            # Find the highest page number in the current page and replace it with the new highest page number
            # until there are no more therapist pages
            while new_highest_page_number and (highest_page_number < MAX_PAGES or MAX_PAGES == 0):
                new_highest_page_number = False
                for page in pages:
                    try:
                        # Find the page numbers on the current page
                        page_number = int(page.text)
                        # If there is a new page number higher than the current highest page number,
                        # Find the highest page number on the current page
                        if page_number > highest_page_number:
                            highest_page_number = page_number
                            page_url = page['href']
                            response = requests.get(page_url, headers=headers)
                            response.raise_for_status()
                            soup = BeautifulSoup(
                                response.content, 'html.parser')
                            pagination_div = soup.find(
                                'div', class_='results-pagination-container')
                            if pagination_div:
                                pages = pagination_div.find_all('a')
                                new_highest_page_number = True
                                break
                    except (ValueError, KeyError) as e:
                        continue

            num_pages = highest_page_number
        # If there are no pagination tags, then it means there is only one or a few therapists on the landing page
        else:
            num_pages = 1
    except Exception as e:
        print(f"Error getting number of pages: {e}")
        num_pages = 1

    return num_pages

# Function to extract data about the therapists on a specific page


def scrape_page_data(soup, province):
    therapists_data = []
    results_container = soup.find('div', class_='results')
    if results_container:
        # Find all therapists on the results page
        therapists = results_container.find_all('div', class_='results-row')
        logger.info("Found " + str(len(therapists)) +
                    " therapists on the page.")
        if therapists:
            for therapist in therapists:
                # Find the tag for the view button and scrape the therapist's url
                view_button = therapist.find('a', class_='profile-title')
                if view_button:
                    view_url = view_button['href']
                    response = fetch_url(view_url)
                    if response.status_code == 200:
                        # Scrape the therapist's data
                        therapist_soup = BeautifulSoup(
                            response.content, 'html.parser')
                        therapist_data = scrape_therapist_data(
                            therapist_soup, province)
                        therapists_data.append(therapist_data)
                    else:
                        print(f"Failed to fetch therapist page: {view_url}")
                else:
                    print("View button not found.")
        else:
            print("No therapist elements found.")
    else:
        print("Results container not found.")
    return therapists_data

# Function to extract a specific therapist's data


def scrape_therapist_data(soup, province):
    therapist_data = {}
    therapist_data['province'] = province  # Add the province to the data
    # TODO: Get rid of
    meta_section = soup.find('div', class_='breadcrumb-xs-hide')
    if meta_section:
        meta_section = meta_section.contents

    # Extract the city
    city_div = soup.find('a', {'data-x': 'breadcrumb-City'}
                         ).find('div', {'itemprop': 'name'})
    if city_div:
        therapist_data['city'] = city_div.text.strip()

    address_divs = soup.find_all('div', class_='address')

    # Extract the street addresses
    street_addresses = []
    for address_div in address_divs:
        street_address = address_div.find('p', class_='address-line')
        if street_address:
            street_addresses.append(street_address.text.strip())

    # Assign street_address_1 and street_address_2 accordingly
    if len(street_addresses) >= 1:
        therapist_data['street_address_1'] = street_addresses[0]
    if (len(street_addresses) >= 2) & (street_addresses[0] != street_addresses[1]):
        therapist_data['street_address_2'] = street_addresses[1]
    else:
        therapist_data['street_address_2'] = None

    # Extract the zip codes
    zip_codes = []
    for address_div in address_divs:
        zip_span = address_div.find('span')
        if zip_span:
            zip_code = zip_span.text.split()[-1]
            zip_codes.append(zip_code)

    # Assign zip_1 and zip_2 accordingly
    if len(zip_codes) >= 1:
        therapist_data['zip_1'] = zip_codes[0]
    if (len(zip_codes) >= 2) & (zip_codes[0] != zip_codes[1]):
        therapist_data['zip_2'] = zip_codes[1]
    else:
        therapist_data['zip_2'] = None

    # Extract the business or person name
    business_name = soup.find('h1', attrs={'class': 'profile-title'})
    if business_name:
        text_business_name = list(business_name.stripped_strings)
        therapist_data['person/business_name'] = ' '.join(text_business_name)
    else:
        raise ValueError("Business or person name not found in the profile.")

    # Extract the title
    title = soup.find('h2', class_='profile-suffix-heading')
    if title:
        suffix_containers = title.find_all(
            'span', class_='profile-suffix-container')
        title_text = ''
        for container in suffix_containers:
            suffixes = container.find_all(
                'span', class_='glossary-tooltip-link')
            for suffix in suffixes:
                title_text += suffix.text.strip() + ', '
        # Remove the trailing comma and space
        therapist_data['title'] = title_text[:-2]

    # Extract the telephone
    telephone_span = soup.find('a', attrs={'class': 'phone-icon-ctr'})
    if telephone_span:
        therapist_data['telephone'] = telephone_span.text.strip()
    else:
        therapist_data['telephone'] = None

    # Extract the insurance providers
    insurance = soup.find('div', class_='insurance')
    if insurance:
        insurance_list = []
        insurance_spans = insurance.find_all('span')
        for span in insurance_spans:
            insurance_list.append(span.text.strip())
        therapist_data['insurance'] = insurance_list
    else:
        therapist_data['insurance'] = None

    # Extract the specialties and expertise
    specialties_and_expertise = []
    specialty_attributes_section = soup.find(
        'div', class_='specialty-attributes-section')
    if specialty_attributes_section:
        attributes_groups = specialty_attributes_section.find_all(
            'div', class_='attributes-group')
        for group in attributes_groups:
            attributes_list = group.find_all('span', class_='attribute_base')
            for attribute in attributes_list:
                specialties_and_expertise.append(attribute.text.strip())
    therapist_data['specialties_and_expertise'] = specialties_and_expertise

    # Extract price

    other_price_div = soup.find('div', class_='fees')

    if other_price_div:
        price_text = other_price_div.get_text()
        text_list = price_text.replace('\n\n', '').splitlines()
        # Remove empty strings
        text_list = str([text.strip() for text in text_list if text.strip()])

        individual = re.search(r'Individual Sessions \$([0-9]+)', text_list)
        couple = re.search(r'Couple Sessions \$([0-9]+)', text_list)

        individual_price = individual.group(1) if individual else None
        couple_price = couple.group(1) if couple else None

        therapist_data['individual_price'] = individual_price
        therapist_data['couple_price'] = couple_price
    else:
        therapist_data['individual_price'] = None
        therapist_data['couple_price'] = None

    # Extract types of therapy
    types_of_therapy = []
    therapy_group_divs = soup.find_all('div', class_='attributes-group')
    for div in therapy_group_divs:
        if div.find('h3', class_='attributes-group-title').text.strip() == 'Types of Therapy':
            ul_tag = div.find('ul', class_='section-list')
            if ul_tag:
                li_tags = ul_tag.find_all('li')
                for li_tag in li_tags:
                    span_tag = li_tag.find('span', class_='attribute_base')
                    if span_tag:
                        types_of_therapy.append(span_tag.text.strip())

    therapist_data['types_of_therapy'] = types_of_therapy

    # Extract age
    ages = []
    client_focus_div = soup.find('div', class_='client-focus-container-small')
    if client_focus_div:
        age_divs = client_focus_div.find_all('div', class_='client-focus-tile')
        for age_div in age_divs:
            if 'Age' in age_div.text:
                age_items = age_div.find_all('div', class_='client-focus-item')
                for item in age_items:
                    age_span = item.find(
                        'span', class_='client-focus-description')
                    if age_span:
                        # Remove trailing comma
                        ages.append(age_span.text.strip().rstrip(' ,'))

    therapist_data['ages'] = ages

    return therapist_data

# Function to save data to csv files, per province


def save_to_csv(data, city, datetimestring=''):
    filename = f'therapists_{city}_{datetimestring}.csv'
    openmethod = 'a' if os.path.exists(filename) else 'w'
    if data:
        with open(filename, openmethod, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            if openmethod == 'w':
                writer.writeheader()
            for therapist in data:
                writer.writerow(therapist)
    else:
        with open(filename, openmethod, newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if openmethod == 'w':
                writer.writerow(['province', 'city', 'street_address_1', 'street_address_2', 'zip_1', 'zip_2', 'person/business_name', 'title',
                                'telephone', 'insurance', 'specialties_and_expertise', 'individual_price', 'couple_price', 'types_of_therapy', 'ages'])

# Function to scrape data from Psychologytoday.com


def main():
    provinces = ["on"]
    cities = ["ottawa"]
    datetimestring = time.strftime("%Y-%m-%d_%H:%M:%S")

    for province in provinces:
        for city in cities:
            scrape_city_data(province, city, datetimestring)
    print("Scraping completed.")


if __name__ == "__main__":
    main()
