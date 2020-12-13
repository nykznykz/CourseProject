
# Basic Collaborative Filtering

This is an attempt to reproduce the basic collaborative filtering idea taught in UIUC CS410 Fall 2020 class.

## How to use


    usage: "python collaborative_filtering.py <user_id>"
    for example, try: "python collaborative_filtering.py 3419993"
    
    optionals:
    	[—-use-average-on-non-rated=1/0] ==> When set to 0, disable the usage of user's average rating on non-rated recipes. Otherwise, the usage is enabled.
    	[--use-pearson=1/0] ==> When the value is 1, the similarity measure will use Pearson correlation coefficient method. Otherwise, Cosine method is used.
    	[-i REVIEWS_CSV_PATH] ==> Path to CSV path with required fields of ['rating', 'recipe_id', 'user_id']. Default path is ../data/all_users.csv.
    	[-k TOP_K_RESULT] ==> Number of recipes the recommendation will filter for the given user's recommendation. The default is 10 results.
    	[-p NUM_OF_PROCESSES] ==> Number of processes used in the parallel processing of the filtering. The default is 20 processes.
    	[-r RECIPE_ID_1 RECIPE_ID_2 …. RECIPE_ID_N] ==> Recipe candidates for the filtering. The default is all non-rated recipes of the given user are the candidates.

## Sample run

    > mdikraprasetya-macbookpro% python collaborative_filtering.py 3419993
    
    > Done filtering 1127 recipes for user 3419993 (out of 54544 users) in 15.87 second(s).
    
    > Top-10 result of recipes to recommend for user 3419993:
    
    > 1. Recipe 223042 with rating prediction of 5.00079.
    
    > 2. Recipe 220854 with rating prediction of 5.00048.
    
    > 3. Recipe 239230 with rating prediction of 5.00048.
    
    > 4. Recipe 219077 with rating prediction of 5.00042.
    
    > 5. Recipe 220597 with rating prediction of 5.00040.
    
    > 6. Recipe 220127 with rating prediction of 5.00038.
    
    > 7. Recipe 239993 with rating prediction of 5.00035.
    
    > 8. Recipe 232799 with rating prediction of 5.00035.
    
    > 9. Recipe 231009 with rating prediction of 5.00031.
    
    > 10. Recipe 236320 with rating prediction of 5.00030.
