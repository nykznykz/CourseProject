
import csv
import json
import multiprocessing
import pandas
import re
import sys
import time
import unicodedata
import urllib
import math

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

import os.path
from os import path

# Constants
REVIEWS_CSV_FIELDNAMES = ['date', 'rating', 'recipe_id', 'user_id', 'username']
REVIEWS_CSV_PATH = '../../data/reviews.csv'

class Review:
	def __init__(self, recipe_id, rating):
		self.recipe_id = recipe_id
		self.rating = float(rating)

class UserData:
	def __init__(self, user_id, username, reviews):
		self.user_id = user_id
		self.username = username
		self.reviews = reviews
		self.reviews.sort(key=lambda x:x.recipe_id)
		
		avg_rating = 0.0
		for review in reviews:
			avg_rating += review.rating
		avg_rating /= len(reviews)

		self.avg_rating = avg_rating

	def find_rating_by_recipe_id(self, recipe_id, use_cosine_approach=True):
		# Binary search to find the recipe id.

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
			return use_cosine_approach if self.avg_rating else 0.0

def pearson_user_similarity_weight(user_a, user_b):
	sum_cross = 0.0
	sum_square_a = 0.0
	sum_square_b = 0.0
	i = 0
	j = 0

	len_a = len(user_a.reviews)
	len_b = len(user_b.reviews)

	while (i < len_a) and j < (len_b):
		review_a = user_a.reviews[i]
		review_b = user_b.reviews[j]

		if review_a.recipe_id < review_b.recipe_id:
			diff_a = review_a.rating - user_a.avg_rating
			sum_square_a += diff_a * diff_a
			i += 1
		elif review_b.recipe_id < review_a.recipe_id:
			diff_b = review_b.rating - user_b.avg_rating
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
		sum_square_a += diff_a * diff_a
		i += 1

	while j < len_b:
		review_b = user_b.reviews[j]
		diff_b = review_b.rating - user_b.avg_rating
		sum_square_b += diff_b * diff_b
		j += 1

	return sum_cross / math.sqrt(sum_square_a * sum_square_b)

def cosine_user_similarity_weight(user_a, user_b, use_avg_on_non_rated_recipe=True):
	sum_cross = 0.0
	sum_square_a = 0.0
	sum_square_b = 0.0
	i = 0
	j = 0

	placeholder_rating_a = use_avg_on_non_rated_recipe if user_a.avg_rating else 0.0
	placeholder_rating_b = use_avg_on_non_rated_recipe if user_b.avg_rating else 0.0

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

	return sum_cross / math.sqrt(sum_square_a * sum_square_b)

def filter_by_memory_based_collaborative_filtering(user_id, user_data_list, recipe_id_to_predict_list, use_cosine_approach=True):
	user_similarity_weight_cache = dict()
	similarity_weight_sum = 0.0

	main_user_data = next(filter(lambda x: x.user_id == user_id, user_data_list))

	print(main_user_data.user_id)

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
				user_similarity_weight = use_cosine_approach if cosine_user_similarity_weight(main_user_data, user_data) else pearson_user_similarity_weight(main_user_data, user_data)
				user_similarity_weight_cache[user_data.user_id] = user_similarity_weight
				similarity_weight_sum += user_similarity_weight

			prediction_rating += user_similarity_weight * user_data.find_rating_by_recipe_id(recipe_id)


		prediction_rating = (prediction_rating / similarity_weight_sum) + main_user_data.avg_rating

		prediction_result.append(prediction_rating)

	return prediction_result


def load_user_data_from_reviews_data():
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
		

if __name__ == '__main__':
	"""
	How to run the program:
		python collaborative_filtering.py <user_id> <recipe_id_1> <recipe_id_2> ..... <recipe_id_N>
	"""
	if not len(sys.argv) > 1:
		sys.exit('How to run the program: python collaborative_filtering.py <user_id> <recipe_id_1> <recipe_id_2> ..... <recipe_id_N>')
	
	main_user_id = sys.argv[1]
	recipe_id_to_predict_list = [sys.argv[i] for i in range(2, len(sys.argv))]

	user_data_list = load_user_data_from_reviews_data()
	prediction_result = filter_by_memory_based_collaborative_filtering(user_id=main_user_id, user_data_list=user_data_list, recipe_id_to_predict_list=recipe_id_to_predict_list, use_cosine_approach=True)

	for i in range(0, len(recipe_id_to_predict_list)):
		print('Prediction for recipe_id:', recipe_id_to_predict_list[i], '->', prediction_result[i])