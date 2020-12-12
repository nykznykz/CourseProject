
import csv
import json
import multiprocessing
import pandas
import re
import sys
import time
import unicodedata
import urllib

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

import os.path
from os import path

# Constants
RECIPE_CSV_FIELDNAMES = ['id', 'url', 'title', 'summary', 'category', 'breadcrumb', 'rating_average',
			          	 'rating_count', 'rating_detail', 'info', 'ingredients', 'directions', 'notes',
			          	 'nutrition', 'main_image', 'ugc_image']

RESULT_CSV_PATH = '../data/recipes.csv'


def is_valid_recipe_url(url):
	"""Check whether the given url is a valid recipe url.

	Args:
		url: Url to check.

	Returns:
		True if the given url is a valid recipe url.
	"""
	return url.startswith('https://www.allrecipes.com/recipe')

def clean_url(url):
	"""Clean the given url into the expected format of a recipe url. Invalid url will be marked as None.

	Args:
    	url: Url to clean.

    Returns:
		Recipe url with the expected format (e.g., 'https://www.allrecipes.com/recipe/99970/chicken-cotija/').
		Invalid url is returned as None instead.
	"""
	url = url.split('?')[0]

	root_url = 'https://www.allrecipes.com'

	if not url.startswith(root_url):
		url = root_url + url

	if not is_valid_recipe_url:
		return None

	return url

def recipe_id_from_recipe_url(url):
	"""Key function for sorting recipe urls. The sort will be done by the recipe id.

	Args:
		url: A recipe url (e.g., 'https://www.allrecipes.com/recipe/99970/chicken-cotija/')

	Returns:
		The key for list sort function, which is the recipe id found in the given url.
	"""
	return int(url.split('/')[4])

def recipe_cache_path(batch_id):
	"""Recipe cache path with the given batch id.

	Args:
		batch_id: Batch ID assigned to the process which generated the recipe cache.

	Returns:
		Path for the recipe cache.
	"""
	return 'cache/recipe_scrape_{}_cache.csv'.format(batch_id)

def clean_url_list(urls, should_clean_url=False):
	"""Clean the given list of urls: remove invalid urls, redundant urls, and sort them in lexicographic order.

	Args:
    	urls: List of url
    	should_clean_url: If True, the function will iterate through every url and clean the url if necessary.

    Returns:
		Sorted list of unique recipe urls.
	"""
	if should_clean_url:
		new_urls = []
		for i in range(0,len(urls)):
			url = clean_url(urls[i])
			if url != None:
				new_urls.append(url)
		urls = new_urls

	urls = list(set(urls))
	urls.sort(key=recipe_id_from_recipe_url)
	return urls

def category_name_from_category_root_url(category_root_url):
	"""Category name from the given root URL of the category.

	Args:
		category_root_url: Root URL of the category.

	Returns:
		Category name.
	"""
	return category_root_url.rsplit("/",2)[1]

def clean_text(text):
	""" Replace all fractional non-ascii characters.

	Args:
		text: Text to clean.

	Returns:
		Cleaned text with fractional unicode replaced, has non-ascii characters replaced, and has unnecessary whitespace removed.
	"""
	for char in '¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞↉':
		normalized = unicodedata.normalize('NFKC',char)
		text.replace(char, normalized)

	text = text.encode('ascii',errors='ignore').decode('utf-8')		# Remove non-ascii characters.
	text = re.sub('\s+',' ',text)		# Replace repeated whitespaces with a single space.
	text = text.strip()		# Clean unnecessary leading or trailing whitespaces.
	return text

def scrape_root_url(root_url):
	"""Scrape the root url to get category root urls. The main carousel nav is the source of category root urls.

	Args:
    	root_url: Root url of the site to scrape.

    Returns:
		A list of category urls.
	"""
	options = Options()
	options.headless = True
	driver = webdriver.Chrome('./chromedriver',options=options)

	category_root_urls = []

	try:
		cache_path = 'cache/category_root_urls_cache.json'

		if path.exists(cache_path):
			with open(cache_path, 'r') as json_file:
				category_root_urls = json.load(json_file)
		else:
			driver.get(root_url)
			soup = BeautifulSoup(driver.execute_script('return document.body.innerHTML'),'html.parser')

			for link_holder in soup.find_all(class_='carouselNav__link recipeCarousel__link'):
				url = link_holder['href']
				category_root_urls.append(url)

			with open(cache_path, 'w') as json_file:
				json.dump(category_root_urls, json_file)
	finally:
		driver.close()
		driver.quit()

	print('Number of category found: ', len(category_root_urls))
	return category_root_urls

def scrape_single_category_root_url(category_root_url, driver):
	"""Scrape the given category root url for a list of recipe urls.

	Args:
    	category_root_url: Category root url to scrape.
    	driver: Selenium chrome driver used for scraping.

    Returns:
		A list of recipe urls scraped from the category root url.
	"""
	json_data = {}

	category_name = category_name_from_category_root_url(category_root_url)
	cache_path = 'cache/' + category_name + '_cache.json'

	if path.exists(cache_path):
		with open(cache_path, 'r') as json_file:
			json_data = json.load(json_file)
	else:
		json_data = {
			'category_name': category_name,
			'category_url': category_root_url,
			'last_page': 0,
			'recipe_urls_length': 0,
			'recipe_urls': [],
			'timestamp': 0,
		}

	urls = clean_url_list(urls=json_data['recipe_urls'], should_clean_url=True)

	print('Category: ', category_name, '. Number of recipe found: ', len(urls))

	page_index = json_data['last_page']+1
	while True:
		page_url = category_root_url + '?page=' + str(page_index)
		print('Looking at', page_url, '...')

		driver.get(page_url)
		time.sleep(0.25)
		soup = BeautifulSoup(driver.execute_script('return document.body.innerHTML'),'html.parser')
		
		is_new_recipe_found = False

		for link_holder in [container.find(class_='card__titleLink') for container in soup.find_all(class_='card__detailsContainer')]:
			url = clean_url(link_holder['href'])
			if url != None:
				urls.append(url)
				is_new_recipe_found = True

		for link_holder in [container.find(class_='tout__titleLink') for container in soup.find_all(class_='component tout')]:
			url = clean_url(link_holder['href'])
			if url != None:
				urls.append(url)
				is_new_recipe_found = True

		for link_holder in [container.find(class_='fixed-recipe-card__title-link') for container in soup.find_all(class_='fixed-recipe-card')]:
			url = clean_url(link_holder['href'])
			if url != None:
				urls.append(url)
				is_new_recipe_found = True

		if not is_new_recipe_found:
			break

		json_data['last_page'] = page_index
		
		print('Category: ', category_name, '. Number of recipe found: ', len(urls))

		# Save data per 100 page indices.
		if page_index % 100 == 0:
			urls = clean_url_list(urls=json_data['recipe_urls'])
			json_data['recipe_urls'] = urls
			json_data['recipe_urls_length'] = len(urls)
			json_data['timestamp'] = time.time()
			
			with open(cache_path, 'w') as json_file:
				json.dump(json_data, json_file)

		page_index += 1


	urls = clean_url_list(urls=json_data['recipe_urls'])
	json_data['recipe_urls'] = urls
	json_data['recipe_urls_length'] = len(urls)
	json_data['timestamp'] = time.time()
	
	with open(cache_path, 'w') as json_file:
		json.dump(json_data, json_file)

	return json_data['recipe_urls']

def scrape_category_root_urls(category_root_urls):
	"""Scrape the given list of root urls.

	Args:
		category_root_urls: List of category root urls to scrape.

    Returns:
		True if the scraping has been completed for all categories.
	"""
	options = Options()
	options.headless = True
	driver = webdriver.Chrome('./chromedriver',options=options)

	try:
		for category_root_url in category_root_urls:
			scrape_single_category_root_url(category_root_url, driver)
	finally:
		driver.close()
		driver.quit()
	return True

def process_category_root_urls_in_parallel(category_root_urls, num_of_process=5):
	"""Process the given list of root urls in parallel using a simple multiprocessing where each process is responsible for processing the same number of categories.

	Args:
		category_root_urls: List of category root url to scrape.
		num_of_process: Number of process that invoked at the same time for multi-processing. Defaults to 5.

    Returns:
		True if all the processes have finished running.
	"""
	start_time = time.perf_counter()

	categories_len = len(category_root_urls)
	num_of_category_per_process = categories_len / num_of_process
	processes = []

	for i in range(num_of_process):
		start_index = int(i * num_of_category_per_process)
		end_index = int((i+1) * num_of_category_per_process)
		process = multiprocessing.Process(target=scrape_category_root_urls, args=[category_root_urls[start_index:end_index]])
		process.start()
		processes.append(process)

	for process in processes:
		process.join()

	finish_time = time.perf_counter()
	print('Done scraping', categories_len, 'categories in ', round(finish_time-start_time, 2), 'second(s).')

	return True

def coalesce_recipe_sources_from_category_cache(category_root_urls):
	"""Combine all found urls from each category root urls.

	Args:
		category_root_urls: List of category root url that has been scraped.

    Returns:
		List of recipe urls in json format where key 'url' contains the url, and key 'categories' contains the category names associated with the url.
	"""
	recipe_source_dict = dict()
	for category_root_url in category_root_urls:
		category_name = category_name_from_category_root_url(category_root_url)
		cache_path = 'cache/' + category_name + '_cache.json'

		if path.exists(cache_path):
			with open(cache_path, 'r') as json_file:
				category_json_data = json.load(json_file)

			for url in category_json_data['recipe_urls']:
				if url in recipe_source_dict:
					recipe_source_dict[url].append(category_json_data['category_name'])
				else:
					recipe_source_dict[url] = [category_json_data['category_name']]

	combined_recipe_sources = []
	for url, categories in recipe_source_dict.items():
		combined_recipe_sources.append({
			'url': url,
			'categories': categories,
		})

	combined_recipe_sources_json = {
		'recipe_sources_len': len(combined_recipe_sources),
		'recipe_sources': combined_recipe_sources,
	}
	with open('cache/combined_recipe_urls_cache.json', 'w') as json_file:
		json.dump(combined_recipe_sources_json, json_file)

	return combined_recipe_sources

def scrape_single_recipe_url(recipe_url, recipe_category, driver):
	"""Scrape recipe contents from a single recipe url.

	Args:
		recipe_url: URL of the recipe page to scrape.
		recipe_category: List of categories associated with the recipe page.
		driver: Selenium chrome driver used for scraping.

    Returns:
		Recipe content packaged in a dictionary. Key-value ma
	"""
	driver.get(recipe_url)
	time.sleep(0.05)
	soup = BeautifulSoup(driver.execute_script('return document.body.innerHTML'),'html.parser')

	# Recipe ID
	recipe_id = recipe_id_from_recipe_url(recipe_url)

	# Recipe Title
	try:
		recipe_title = clean_text(soup.find(class_='intro article-info').find(class_='headline heading-content').get_text())
	except:
		# When title scrape is failed, mark the recipe's title with an empty string
		# TODO(mdp9): Find out why 'intro article-info' class is not found once in a while.
		recipe_title = ''

	# Recipe Summary
	recipe_summary = clean_text(soup.find(class_='recipe-summary').get_text())

	# Recipe Breadcrumbs
	recipe_breadcrumbs = [clean_text(breadcrumb.get_text()) for breadcrumb in soup.find(class_='content-breadcrumbs').find_all(class_='breadcrumbs__title')]

	# Recipe Rating
	recipe_rating_average = 0
	recipe_rating_count = 0
	recipe_rating_detail = dict()
	try:
		for rating_item in soup.find(class_='recipe-ratings-list').find_all(class_='rating'):
			rating_item_stars = int(rating_item.find(class_='rating-stars').find(text=True, recursive=False))
			rating_item_count = int(rating_item.find(class_='rating-count').get_text())
			recipe_rating_average += rating_item_stars * rating_item_count
			recipe_rating_count += rating_item_count
			recipe_rating_detail[rating_item_stars] = rating_item_count
	except:
		# When rating scrape is failed, mark the recipe's rating with -1.
		# TODO(mdp9): Find out why 'recipe-ratings-list' class is not found once in a while.
		recipe_rating_average = -1

	if recipe_rating_count > 0:
		recipe_rating_average /= recipe_rating_count

	# Recipe Info
	recipe_info = dict()
	for info_item in soup.find(class_='recipe-info-section').find_all(class_='recipe-meta-item'):
		info_header = clean_text(info_item.find(class_='recipe-meta-item-header').get_text()).split(':')[0].lower()
		info_body = clean_text(info_item.find(class_='recipe-meta-item-body').get_text())

		recipe_info[info_header] = info_body

	# Recipe Ingredients
	recipe_ingredients = ''

	for ingredients_section in soup.find_all(class_='ingredients-section__fieldset'):
		# Seperate each section with double new line.
		if recipe_ingredients != '':
			recipe_ingredients += '\n\n'
		recipe_ingredients += '. '.join(clean_text(text=ingredients_section_legend.get_text()) for ingredients_section_legend in ingredients_section.find_all(class_='ingredients-section__legend')) + '\n'
		recipe_ingredients += '. '.join(clean_text(text=ingredients_item.get_text()) for ingredients_item in ingredients_section.find_all(class_='ingredients-item'))

	# Recipe Directions
	recipe_directions = ''

	for directions_section in soup.find_all(class_='instructions-section__fieldset'):
		# Seperate each section with double new line.
		if recipe_directions != '':
			recipe_directions += '\n\n'
		recipe_directions += '. '.join(clean_text(directions_item.get_text()) for directions_item in directions_section.find_all(class_='instructions-section-item'))

	# Recipe Notes
	recipe_notes = '. '.join(clean_text(notes.get_text()) for notes in soup.find_all(class_='component recipe-notes'))

	# Recipe Nutrition
	recipe_nutrition = '. '.join(clean_text(nutrition.get_text()) for nutrition in soup.find_all(class_='nutrition-section container'))

	# Recipe Images
	main_image_container = soup.find(class_='image-container').find(class_='lazy-image')
	recipe_main_image = main_image_container['data-src'] if main_image_container != None else None

	recipe_ugc_images = [ugc_photos_link.find('img')['src'] for ugc_photos_link in soup.find(class_='lead-content-wrapper').find_all(class_='ugc-photos-link')]

	# Populate data
	recipe_json = {
		'id': recipe_id,
		'url': recipe_url,
		'title': recipe_title,
		'summary': recipe_summary,
		'category': recipe_category,
		'breadcrumb': recipe_breadcrumbs,
		'rating_average': recipe_rating_average,
		'rating_count': recipe_rating_count,
		'rating_detail': recipe_rating_detail,
		'info': recipe_info,
		'ingredients': recipe_ingredients,
		'directions': recipe_directions,
		'notes': recipe_notes,
		'nutrition': recipe_nutrition,
		'main_image': recipe_main_image,
		'ugc_image': recipe_ugc_images,
	}

	return recipe_json

def scrape_recipe_sources(recipe_sources, batch_id):
	"""Scrape the given list of recipe sources. The scraping is processed with a process assigned with the given batch ID.

	Args:
		recipe_sources: List of recipe sources. A source contains a 'url', the recipe URL, and 'categories', the categories associated with the recipe page.
		batch_id: Batch ID assigned to the process where the scaping is conducted.

    Returns:
		True if the scraping has been completed for all recipe sources.
	"""
	options = Options()
	options.headless = True
	driver = webdriver.Chrome('./chromedriver',options=options)

	cache_path = recipe_cache_path(batch_id)

	scraped_ids = set()
	if path.exists(cache_path):
		scraped_ids = set([row[0] for row in pandas.read_csv(RESULT_CSV_PATH, usecols=['id']).values])
	else:
		with open(cache_path, 'w') as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=RECIPE_CSV_FIELDNAMES)
			writer.writeheader()

	try:
		with open(cache_path, 'a') as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=RECIPE_CSV_FIELDNAMES)

			for i, recipe_source in enumerate(recipe_sources, start=1):
				print('Batch {} processing recipe #{}'.format(batch_id, i))

				recipe_id = recipe_id_from_recipe_url(recipe_source['url'])
				if recipe_id in scraped_ids:
					continue

				recipe_content = None

				# Sometimes the driver experiences a connection failure. Keep trying to scrape one page until it succeeded.
				try:
					recipe_content = scrape_single_recipe_url(recipe_source['url'], recipe_source['categories'], driver)
				except:
					# Instantiate a new driver.
					try:
						driver.close()
						driver.quit()
					finally:
						time.sleep(1)
						driver = webdriver.Chrome('./chromedriver',options=options)
						recipe_content = None

				writer.writerow(recipe_content)

	finally:
		driver.close()
		driver.quit()

	return True

def remove_scraped_recipe_from_list(recipe_sources):
	"""Remove all the previously scraped recipe from the given recipe source list.

	Args:
		recipe_sources: List of recipe sources. A source contains a 'url', the recipe URL, and 'categories', the categories associated with the recipe page.

    Returns:
		Trimmed recipe sources which all member of the list has not been scraped yet.
	"""
	scraped_ids = set()
	if path.exists(RESULT_CSV_PATH):
		scraped_ids = set([row[0] for row in pandas.read_csv(RESULT_CSV_PATH, usecols=['id']).values])

	new_recipe_sources = []
	for recipe_source in recipe_sources:
		recipe_id = recipe_id_from_recipe_url(recipe_source['url'])

		if recipe_id in scraped_ids:
			continue

		new_recipe_sources.append(recipe_source)

	print('Number of skipped recipes: {}. They are skipped because their info have been scraped before.'.format(len(recipe_sources)-len(new_recipe_sources)))
	return new_recipe_sources


def process_recipe_sources_in_parallel(recipe_sources, num_of_process=5):
	"""Process the given list of recipe sources in parallel using a simple multiprocessing where each process is responsible for processing the same number of categories.

	Args:
		recipe_sources: List of recipe sources. A source contains a 'url', the recipe URL, and 'categories', the categories associated with the recipe page.
		num_of_process: Number of process that invoked at the same time for multi-processing. Defaults to 5.

    Returns:
		True if all the processes have finished running and after the csv caches have been combined into one csv.
	"""
	start_time = time.perf_counter()

	recipe_sources = remove_scraped_recipe_from_list(recipe_sources)
	recipe_sources_len = len(recipe_sources)

	num_of_recipe_per_process = recipe_sources_len / num_of_process
	processes = []

	for i in range(num_of_process):
		start_index = int(i * num_of_recipe_per_process)
		end_index = int((i+1) * num_of_recipe_per_process)
		process = multiprocessing.Process(target=scrape_recipe_sources, args=[recipe_sources[start_index:end_index],i])
		process.start()
		processes.append(process)

	for process in processes:
		process.join()

	finish_time = time.perf_counter()
	print('Done scraping', recipe_sources_len, 'recipes in ', round(finish_time-start_time, 2), 'second(s).')

	coalesce_recipe_scrape_caches()

	return True

def coalesce_recipe_scrape_caches():
	"""Combine the previously scraped recipes that were put into separate caches into a single csv file.

    Returns:
		True if the recipe caches have successfully combined into one csv.
	"""
	if not path.exists(RESULT_CSV_PATH):
		with open(RESULT_CSV_PATH, 'w') as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=RECIPE_CSV_FIELDNAMES)
			writer.writeheader()

	# Coalesce recipe caches one by one.
	batch_id = 0
	while True:
		cache_path = recipe_cache_path(batch_id)

		if not path.exists(cache_path):
			# Stops when the given cache path is not found. Cache IDs are not sparse.
			break

		print('Combining data from cached recipes batch {}...'.format(batch_id))

		with open(RESULT_CSV_PATH, 'a') as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=RECIPE_CSV_FIELDNAMES)
			with open(cache_path) as cache_csv_file:
				reader = csv.DictReader(cache_csv_file)
				for row in reader:
					writer.writerow(row)

		# Remove old cache path
		os.remove(cache_path)

		batch_id += 1
		
	# Sort the csv.
	sorted_csv_data = None
	with open(RESULT_CSV_PATH, 'r') as csv_file:
		reader = csv.DictReader(csv_file, fieldnames=RECIPE_CSV_FIELDNAMES)
		next(reader, None)	# Skip the header
		sorted_csv_data = sorted(reader, key=lambda row:int(row['id']), reverse=False)

	with open(RESULT_CSV_PATH, 'w') as csv_file:
		writer = csv.DictWriter(csv_file, fieldnames=RECIPE_CSV_FIELDNAMES)
		writer.writeheader()
		for row in sorted_csv_data:
			writer.writerow(row)

	return True

if __name__ == '__main__':
	if not os.path.exists('chromedriver'):
		sys.exit('ERROR: A chromedriver is not found at current directory.\nPlease download at https://chromedriver.chromium.org/downloads.')

	if not os.path.exists('cache'):
		os.makedirs('cache')

	# Update recipe with remaining caches, just in case the program was interrupted previously.
	coalesce_recipe_scrape_caches()
	
	# Scrape scrape scrape!
	root_url = 'https://www.allrecipes.com/recipes/'
	category_root_urls = scrape_root_url(root_url)
	process_category_root_urls_in_parallel(category_root_urls)
	process_recipe_sources_in_parallel(coalesce_recipe_sources_from_category_cache(category_root_urls))