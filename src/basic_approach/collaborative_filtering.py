
import csv
import math
import sys
import time

""" Constants """
REVIEWS_CSV_FIELDNAMES = ['date', 'rating', 'recipe_id', 'user_id', 'username']	# Expected field names of the reviews CSV data.
REVIEWS_CSV_PATH = '../data/reviews.csv'	# Default path to the reviews CSV data.
EPS = 1e-5	# Epsilon to use for optimizations (i.e., returning EPS value instead of a flat 0.0 in the calculation)

class Review:
	"""A data structure for a single user review, consisting two parameters: a recipe ID and its rating (1-5)."""

	def __init__(self, recipe_id, rating):
		self.recipe_id = recipe_id
		self.rating = float(rating)

class UserData:
	"""A data structure for a single user's data, consisting three parameters: a user ID, a username, and a list of reviews (Review class objects)."""

	def __init__(self, user_id, username, reviews):
		self.user_id = user_id
		self.username = username
		self.reviews = reviews
		self.reviews.sort(key=lambda x:int(x.recipe_id))
		
		avg_rating = 0.0
		if len(reviews) > 0:
			for review in reviews:
				avg_rating += review.rating
			avg_rating /= len(reviews)
		else:
			avg_rating = EPS

		self.avg_rating = avg_rating

	def find_rating_by_recipe_id(self, recipe_id, use_avg_on_non_rated_recipe=True):
		"""Find the rating od the given recipe ID.

		Args:
	    	recipe_id: String of recipe ID.
	    	use_avg_on_non_rated_recipe: If set to True, non-rated item will be assigned with user average rating value. Otherwise, non-rated item is treated as EPS rating. Defaults to True.

	    Returns:
			Rating of the given recipe ID.
		"""

		i = 0
		j = len(self.reviews)

		while i < j:
			mid = (i + j) >> 1
			if self.reviews[mid].recipe_id >= recipe_id:
				j = mid
			else:
				i = mid+1

		if j < len(self.reviews) and self.reviews[j].recipe_id == recipe_id:
			return self.reviews[j].rating
		else:
			return self.avg_rating if use_avg_on_non_rated_recipe else EPS

def pearson_user_similarity_weight(user_a, user_b, use_avg_on_non_rated_recipe=False):
	"""User similarity measures by Pearson correlation coefficient measure.

	Args:
    	user_a: UserData object of user A.
    	user_b: UserData object of user B.
    	use_avg_on_non_rated_recipe: If set to True, non-rated item will be assigned with user average rating value. Otherwise, non-rated item is treated as EPS rating. Defaults to True.

    Returns:
		The weight of the similarity of user A of user B.
	"""

	sum_cross = 0.0
	sum_square_a = 0.0
	sum_square_b = 0.0
	i = 0
	j = 0

	placeholder_rating_a = user_a.avg_rating if use_avg_on_non_rated_recipe else EPS
	placeholder_rating_b = user_b.avg_rating if use_avg_on_non_rated_recipe else EPS

	len_a = len(user_a.reviews)
	len_b = len(user_b.reviews)

	while (i < len_a) and j < (len_b):
		review_a = user_a.reviews[i]
		review_b = user_b.reviews[j]

		if review_a.recipe_id < review_b.recipe_id:
			diff_a = review_a.rating - user_a.avg_rating
			diff_b = placeholder_rating_b - user_b.avg_rating
			sum_cross += diff_a * diff_b
			sum_square_a += diff_a * diff_a
			sum_square_b += diff_b * diff_b
			i += 1
		elif review_b.recipe_id < review_a.recipe_id:
			diff_a = placeholder_rating_a - user_a.avg_rating
			diff_b = review_b.rating - user_b.avg_rating
			sum_cross += diff_a * diff_b
			sum_square_a += diff_a * diff_a
			sum_square_b += diff_b * diff_b
			j += 1
		else:
			diff_a = review_a.rating - user_a.avg_rating
			diff_b = review_b.rating - user_b.avg_rating
			sum_cross += diff_a * diff_b
			sum_square_a += diff_a * diff_a
			sum_square_b += diff_b * diff_b
			i += 1
			j += 1

	while i < len_a:
		review_a = user_a.reviews[i]
		diff_a = review_a.rating - user_a.avg_rating
		diff_b = placeholder_rating_b - user_b.avg_rating
		sum_cross += diff_a * diff_b
		sum_square_a += diff_a * diff_a
		sum_square_b += diff_b * diff_b
		i += 1

	while j < len_b:
		diff_a = placeholder_rating_a - user_a.avg_rating
		diff_b = review_b.rating - user_b.avg_rating
		sum_cross += diff_a * diff_b
		sum_square_a += diff_a * diff_a
		sum_square_b += diff_b * diff_b
		j += 1

	return (sum_cross + EPS) / math.sqrt((sum_square_a * sum_square_b) + EPS)

def cosine_user_similarity_weight(user_a, user_b, use_avg_on_non_rated_recipe=False):
	"""User similarity measures by Cosine measure.

	Args:
    	user_a: UserData object of user A.
    	user_b: UserData object of user B.
    	use_avg_on_non_rated_recipe: If set to True, non-rated item will be assigned with user average rating value. Otherwise, non-rated item is treated as EPS rating. Defaults to True.

    Returns:
		The weight of the similarity of user A of user B.
	"""
	sum_cross = 0.0
	sum_square_a = 0.0
	sum_square_b = 0.0
	i = 0
	j = 0

	placeholder_rating_a = user_a.avg_rating if use_avg_on_non_rated_recipe else EPS
	placeholder_rating_b = user_b.avg_rating if use_avg_on_non_rated_recipe else EPS

	len_a = len(user_a.reviews)
	len_b = len(user_b.reviews)

	while (i < len_a) and (j < len_b):
		review_a = user_a.reviews[i]
		review_b = user_b.reviews[j]

		if review_a.recipe_id < review_b.recipe_id:
			sum_cross += review_a.rating * placeholder_rating_b
			sum_square_a += review_a.rating * review_a.rating
			sum_square_b += placeholder_rating_b * placeholder_rating_b
			i += 1
		elif review_b.recipe_id < review_a.recipe_id:
			sum_cross += placeholder_rating_a * review_b.rating
			sum_square_a += placeholder_rating_a * placeholder_rating_a
			sum_square_b += review_b.rating * review_b.rating
			j += 1
		else:
			sum_cross += review_a.rating * review_b.rating
			sum_square_a += review_a.rating * review_a.rating
			sum_square_b += review_b.rating * review_b.rating
			i += 1
			j += 1

	while i < len_a:
		review_a = user_a.reviews[i]
		sum_cross += review_a.rating * placeholder_rating_b
		sum_square_a += review_a.rating * review_a.rating
		sum_square_b += placeholder_rating_b * placeholder_rating_b
		i += 1

	while j < len_b:
		review_b = user_b.reviews[j]
		sum_cross += placeholder_rating_a * review_b.rating
		sum_square_a += placeholder_rating_a * placeholder_rating_a
		sum_square_b += review_b.rating * review_b.rating
		j += 1

	return (sum_cross + EPS) / math.sqrt((sum_square_a * sum_square_b) + EPS)


def filter_by_memory_based_collaborative_filtering(user_id, user_data_list, recipe_id_to_predict_list, use_cosine_approach=True, use_avg_on_non_rated_recipe=False):
	"""A basic collaborative filtering approach with memory based approach, taught in UIUC CS410 Fall 2020.

	Args:
    	user_id: String of user ID.
    	user_data_list: List of UserData objects parsed from the reviews data.
    	recipe_id_to_predict_list: List of recipe IDs that the program will predict the rating value.

    Returns:
		List of rating predictions where Xi is a rating prediction of the recipe index-i in the recipe_id_to_predict_list, based on the user with the given user ID.
	"""
	user_similarity_weight_cache = dict()
	similarity_weight_sum = 0.0

	main_user_data = UserData(user_id, '', [])	# Placeholder user data
	for user_data in user_data_list:
		if user_data.user_id == user_id:
			main_user_data = user_data
			break

	prediction_result = []
	for recipe_id in recipe_id_to_predict_list:

		prediction_rating = 0.0

		for user_data in user_data_list:
			if user_data.user_id == user_id:
				continue

			user_similarity_weight = 0.0

			if user_data.user_id in user_similarity_weight_cache:
				user_similarity_weight = user_similarity_weight_cache[user_data.user_id]
			else:
				user_similarity_weight = cosine_user_similarity_weight(main_user_data, user_data, use_avg_on_non_rated_recipe) if use_cosine_approach else pearson_user_similarity_weight(main_user_data, user_data, use_avg_on_non_rated_recipe)

				user_similarity_weight_cache[user_data.user_id] = user_similarity_weight
				similarity_weight_sum += user_similarity_weight

			prediction_rating += user_similarity_weight * (user_data.find_rating_by_recipe_id(recipe_id, use_avg_on_non_rated_recipe) - user_data.avg_rating)

		prediction_rating = max((prediction_rating / similarity_weight_sum) + main_user_data.avg_rating, EPS)

		prediction_result.append(prediction_rating)

	return prediction_result


def load_user_data_from_reviews_data(reviews_csv_path = REVIEWS_CSV_PATH):
	"""Load the user data from the available reviews data.

    Returns:
		List of UserData object parsed from the reviews data.
	"""
	user_reviews_dict = dict()
	user_username_dict = dict()

	with open(REVIEWS_CSV_PATH, 'r') as csv_file:
		reader = csv.DictReader(csv_file, fieldnames=REVIEWS_CSV_FIELDNAMES)
		next(reader, None)	# Skip the header
		for row in reader:
			user_id = row['user_id']
			review = Review(row['recipe_id'], row['rating'])

			user_username_dict[user_id] = row['username']

			if not (user_id in user_reviews_dict):
				user_reviews_dict[user_id] = []

			user_reviews_dict[user_id].append(review)

	return [UserData(user_id, user_username_dict[user_id], review) for user_id, review in user_reviews_dict.items()]

def determine_recipe_to_predict(user_id, user_data_list):
	"""Decide the recipe IDs list that the user with the given user id should try to predict. Basically the objects in the list are the recipes that the user hasn't rated yet.

	Args:
    	user_id: String of user ID.
    	user_data_list: List of UserData objects parsed from the reviews data.

    Returns:
		List of recipe IDs to predict in the collaborative filtering for the given user ID.
	"""
	recipe_id_to_predict_set = set()

	main_user_data = UserData(user_id, '', [])	# Placeholder user data

	for user_data in user_data_list:
		if user_data.user_id == user_id:
			main_user_data = user_data
			continue

		for review in user_data.reviews:
			recipe_id_to_predict_set.add(review.recipe_id)

	for review in main_user_data.reviews:
		if review.recipe_id in recipe_id_to_predict_set:
			recipe_id_to_predict_set.remove(review.recipe_id)

	return list(recipe_id_to_predict_set)		


def print_program_usage_guide():
	""" Print a helpful program usage guide on the terminal."""
	print('')
	print('usage: python collaborative_filtering.py <user_id>')
	print('		for example, try : python collaborative_filtering.py 30079')
	print('optionals:')
	print('		[—-use-average-on-non-rated=1/0] ==> When set to 0, disable the usage of user\'s average rating on non-rated recipes. Otherwise, the usage is enabled.')
	print('		[--use-pearson=1/0] ==> When the value is 1, the similarity measure will use Pearson correlation coefficient method. Otherwise, Cosine method is used.')
	print('		[-i REVIEWS_CSV_PATH] ==> Path to CSV path with expected header of [\'date\', \'rating\', \'recipe_id\', \'user_id\', \'username\']. Default path is ../data/reviews.csv.')
	print('		[-k TOP_K_RESULT] ==> Number of recipes the recommendation will filter for the given user\'s recommendation. The default is 10 results.')
	print('		[-r RECIPE_ID_1 RECIPE_ID_2 …. RECIPE_ID_N] ==> Recipe candidates for the filtering. The default is all non-rated recipes of the given user are the candidates.')
	print('')

def config_from_sys_argv():
	"""Parse the given program execution arguments.

	usage: python collaborative_filtering.py <user_id>
	optionals: [—-use-average-on-non-rated] [--use-pearson=1/0] [-i REVIEWS_CSV_PATH] [-k TOP_K_RESULT] [-r RECIPE_ID_1 RECIPE_ID_2 …. RECIPE_ID_N]	

    Returns:
		List of recipe IDs to predict in the collaborative filtering for the given user ID.
	"""
	argv = sys.argv
	config_dict = dict()
	
	try:
		if not len(argv) > 1:
			raise Exception('Invalid arguments')

		if not argv[1].isdigit():
			raise Exception('Invalid arguments')

		# Default values
		config_dict['main-user-id'] = argv[1]
		config_dict['csv-path'] = REVIEWS_CSV_PATH
		config_dict['use-pearson'] = False
		config_dict['use-average-on-non-rated'] = True
		config_dict['top-k'] = 10

		i = 2
		while i < len(argv):
			if argv[i] == '--use-average-on-non-rated=1':
				config_dict['use-average-on-non-rated'] = True
				i += 1
			elif argv[i] == '--use-average-on-non-rated=0':
				config_dict['use-average-on-non-rated'] = False
				i += 1
			elif argv[i] == '--use-pearson=1':
				config_dict['use-pearson'] = True
				i += 1
			elif argv[i] == '--use-pearson=0':
				config_dict['use-pearson'] = False
				i += 1
			elif argv[i] == '-i':
				config_dict['csv-path'] = argv[i+1]
				i += 2
			elif argv[i] == '-k':
				config_dict['top-k'] = int(argv[i+1])
				i += 2
			elif argv[i] == '-r':
				i += 1
				config_dict['recipe-list'] = []
				while i < len(argv) and argv[i].isdigit():
					config_dict['recipe-list'].append(argv[i])
					i += 1
			else:
				raise Exception('Invalid arguments')
	except:
		print_program_usage_guide()
		sys.exit()

	return config_dict

if __name__ == '__main__':
	config_dict = config_from_sys_argv()
	main_user_id = config_dict['main-user-id']
	user_data_list = load_user_data_from_reviews_data(config_dict['csv-path'])

	if 'recipe-list' in config_dict:
		recipe_id_to_predict_list = config_dict['recipe-list']
	else:
		recipe_id_to_predict_list = determine_recipe_to_predict(main_user_id, user_data_list)

	start_time = time.perf_counter()

	prediction_result = filter_by_memory_based_collaborative_filtering(
		user_id=main_user_id,
		user_data_list=user_data_list, 
		recipe_id_to_predict_list=recipe_id_to_predict_list,
		use_cosine_approach=(not config_dict['use-pearson']),
		use_avg_on_non_rated_recipe=config_dict['use-average-on-non-rated']
	)

	finish_time = time.perf_counter()
	print('Done filtering %d recipes for user %s (out of %d users) in %.2lf second(s).' % (len(recipe_id_to_predict_list), main_user_id, len(user_data_list), round(finish_time-start_time, 2)))

	result_tuple_list = [(recipe_id_to_predict_list[i], float(prediction_result[i])) for i in range(0, len(prediction_result))]
	result_tuple_list.sort(key=lambda x:float(x[1]), reverse=True)

	show_result_len = min(config_dict['top-k'], len(result_tuple_list))

	print('Top-%d result of recipes to recommend for user %s:' % (show_result_len, main_user_id))
	for i in range(0, show_result_len):
		print('%d. Recipe %s with rating prediction of %.5lf.' % (i+1, result_tuple_list[i][0], result_tuple_list[i][1]))

