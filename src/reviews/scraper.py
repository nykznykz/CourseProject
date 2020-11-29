import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import re
import json
from time import sleep, time
import random

class util:
    def __init__(self):
        pass

# load recipes ids
final_recipe_ids = pd.read_csv("../data/recipe_ids.csv")["id"].tolist()
print(final_recipe_ids)

##### user reviews #####
# To search faster through large blocks of HTML Soups, set page size to max 25
# There are < 2500 reviews for all of Chef John's recipes -> 2500/25 = 100 max pages
def get_users(recipe_id):
    '''Returns users in a dictionary for a specific recipe
    '''
    URL = f'https://www.allrecipes.com/recipe/getreviews/?recipeid={recipe_id}&recipeType=Recipe&sortBy=MostHelpful&pagesize=50'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'}
    lst_of_users = []
    for page in range(1,10): # loop through all pages
        params = {'pagenumber': page}
        response = requests.get(URL,headers=headers, params=params)
        soup = BeautifulSoup(response.content,"lxml")
        num_users = len(soup.find_all("h4",{"itemprop":"author"})) # users on a page
        print(num_users)
        if num_users == 0: # if page is blank, break loop
            break
        index = 1
        for i in range(num_users): # loop through users on a page
            user = {}
            user["recipe_id"] = recipe_id
            user["user_id"] = soup.find_all("div",{"class":"recipe-details-cook-stats-container"})[i].find("a")["href"].split("/")[-2]
            user["username"] = re.sub(r'\\r\\n|\s\s','',soup.find_all("h4",{"itemprop":"author"})[i].text)
            user["rating"] = soup.find_all("div",{"class":"stars-and-date-container"})[i]["title"].split(" ")[2]
            user["date"] = soup.find_all("div",{"class":"review-date"})[i]["content"]
            lst_of_users.append(user)
            print(f'Getting review seq: {index} of page {page}')
            index +=1
    return lst_of_users


def get_all_users(final_recipe_ids):
    '''Return all the users as a dataframe get_all_users(final_recipe_ids[0:2])
    '''   
    start_time = time()
    df = pd.DataFrame(columns=['date', 'rating', 'recipe_id', 'user_id', 'username'])
    index = 1
    users = []
    for i in final_recipe_ids:
        start_time = time()
        users.extend(get_users(i))
        print(f'Got users for recipe {index}/{len(final_recipe_ids)}')
        index += 1
        elapsed_time = time() - start_time
        print(elapsed_time)
        #sleep(random.randint(0,3))
    # concat outside of the first loop function for better performance
    lst = []
    for user in users:
        lst.append(pd.DataFrame([user]))
    return pd.concat(lst)


#data = get_all_users(final_recipe_ids[0:1000])
#data.to_csv("../data/reviews.csv",index=False)


data = get_all_users(final_recipe_ids[0:5])
data.to_csv("../data/reviews.csv",index=False)

data = get_all_users(final_recipe_ids[5:10])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)

data = get_all_users(final_recipe_ids[10:100])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)

data = get_all_users(final_recipe_ids[100:200])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)

data = get_all_users(final_recipe_ids[200:400])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)

data = get_all_users(final_recipe_ids[400:600])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)

data = get_all_users(final_recipe_ids[600:800])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)

data = get_all_users(final_recipe_ids[800:1000])
data.to_csv("../data/reviews.csv",index=False,mode='a', header=False)







