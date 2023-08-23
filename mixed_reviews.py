import numpy as np
from sqlalchemy import create_engine
from flask import Flask, render_template, request, url_for, flash, redirect
import requests
from urllib.parse import urlparse

import aspect_based_sentiment_analysis as absa
from collections import defaultdict
from figure_generator import survey

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from api_keys import SECRET_KEY, API_KEY
from sql_strings import LOOKUP_TABLE_ALIAS_QUERY_STRING, LOOKUP_TABLE_INSERT_STRING,\
    REVIEWS_TABLE_INSERT_STRING, REVIEWS_TABLE_QUERY_STRING, POSTGRESQL_CONNECTION_STRING, BUSINESS_TABLE_QUERY_STRING
from params import STRONG_OPINION_THRESHOLD


engine = create_engine(POSTGRESQL_CONNECTION_STRING)

recognizer = absa.aux_models.BasicPatternRecognizer()
nlp = absa.load(pattern_recognizer=recognizer)

app = Flask(__name__)

def steve_score(arr):
    return  ( (arr[2] - arr[1]) / (arr[0] + 0.0000000000001) )

def get_db_connection(db_engine):
    conn = db_engine.connect()
    return conn

@app.route('/')
def index():
    return redirect(url_for("search"))

@app.route('/error')
def error():
    return render_template('error.html')
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/reviews/<business_id>', methods=('GET','POST'))
def reviews(business_id):
    print('VERSION')
    print(business_id)

    total_steve_score_values = defaultdict(lambda: 0)
    
    if request.method in ['GET']:

        analysis_params = []
        conn = get_db_connection(engine)
        
        posts = conn.execute(REVIEWS_TABLE_QUERY_STRING, business_id).fetchall()
        print("POSTS ",posts)

        if posts is None:

           return(redirect(url_for("error"))) 
    
        for post in posts:
            text = post[0]
            print("TEXT ", text)
            total_steve_score_values['total_reviews_surveyed'] = 0 
            completed_task = nlp(text=text, aspects=['food', 'price', 'service', 'bathroom'])
            food, price, service, bathroom = completed_task.examples
                    
            food_scores = food.scores + [steve_score(food.scores)]
            price_scores = price.scores + [steve_score(price.scores)]
            service_scores = service.scores + [steve_score(service.scores)]
            bathroom_scores = bathroom.scores + [steve_score(bathroom.scores)]

            if food_scores[-1] >= STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_food_positives'] += 1
            elif food_scores[-1] <= -1*STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_food_negatives'] += 1
            else:
                total_steve_score_values['steve_food_neutrals'] += 1

            if price_scores[-1] >= STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_price_positives'] += 1
            elif food_scores[-1] <= -1*STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_price_negatives'] += 1
            else:
                total_steve_score_values['steve_price_neutrals'] += 1

            if service_scores[-1] >= STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_service_positives'] += 1
            elif service_scores[-1] <= -1*STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_service_negatives'] += 1
            else:
                total_steve_score_values['steve_service_neutrals'] += 1

            if bathroom_scores[-1] >= STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_bathroom_positives'] += 1
            elif bathroom_scores[-1] <= -1*STRONG_OPINION_THRESHOLD:
                total_steve_score_values['steve_bathroom_negatives'] += 1
            else:
                total_steve_score_values['steve_bathroom_neutrals'] += 1
            

            analysis_params.append([food_scores,price_scores,service_scores,bathroom_scores])            
                
        categories = ['food', 'price', 'service', 'bathroom']
        positives = [total_steve_score_values['steve_food_positives'], total_steve_score_values['steve_price_positives'], total_steve_score_values['steve_service_positives'], total_steve_score_values['steve_bathroom_positives']]
        neutrals = [total_steve_score_values['steve_food_neutrals'], total_steve_score_values['steve_price_neutrals'], total_steve_score_values['steve_service_neutrals'], total_steve_score_values['steve_bathroom_neutrals']]
        negatives = [total_steve_score_values['steve_food_negatives'], total_steve_score_values['steve_price_negatives'], total_steve_score_values['steve_service_negatives'], total_steve_score_values['steve_bathroom_negatives']]

        b1 = plt.barh(categories, positives, color='green')
        b2 = plt.barh(categories, neutrals, left=positives, color='grey')
        b3 = plt.barh(categories, negatives, left=neutrals, color='red')
        plt.legend([b1, b2, b3], ['Positives','Neutrals', 'Negatives'], title="Review Opinions", loc='right')
        #plt.plot()

        category_names = ['Negative', 'Neutral',
                  'Positive']
        results = {
        'Food': [total_steve_score_values['steve_food_negatives'], total_steve_score_values['steve_food_neutrals'], total_steve_score_values['steve_food_positives']],
        'Price': [total_steve_score_values['steve_price_negatives'], total_steve_score_values['steve_price_neutrals'], total_steve_score_values['steve_price_positives']],
        'Service': [total_steve_score_values['steve_service_negatives'], total_steve_score_values['steve_service_neutrals'], total_steve_score_values['steve_service_positives']],
        'Bathroom': [total_steve_score_values['steve_bathroom_negatives'], total_steve_score_values['steve_bathroom_neutrals'], total_steve_score_values['steve_bathroom_positives']]
        }

        survey(results,category_names, business_id)
        
        business_info = conn.execute(BUSINESS_TABLE_QUERY_STRING, business_id).fetchone()
        
        if business_info == None:
            return(redirect(url_for("error")))
        
        path_to_graphic = f'../static/img/{business_id}.png'
        conn.close()

        return render_template('results.html', posts=posts,analysis_params=analysis_params, business_info=business_info, length=len(posts), path_to_graphic=path_to_graphic) 

@app.route('/search', methods=('GET', 'POST'))
def search():
    
    if request.method == 'POST':
        
        conn = get_db_connection(engine)
        url = request.form['url']

        if not url:
            flash('enter a url, yelp_id, alias, or zip code' )

        else:

            if url:
                print(url)
                parsed_url = urlparse(url.lower()) 
                netloc = parsed_url.netloc
                path = parsed_url.path
                
                if (netloc.find('yelp') != -1 or path.find('yelp') != -1):
                     alias = path.split('/')[-1]

                else:
                    redirect(url_for("error"))

                headers = {"accept": "application/json",
                'authorization': f'Bearer {API_KEY}',
                  }

                params = {
                 'limit':50
                  }

                #print(LOOKUP_TABLE_ALIAS_QUERY_STRING.format(alias))
                result = conn.execute(LOOKUP_TABLE_ALIAS_QUERY_STRING, alias)
                yelp_id = result.fetchone()
                
                print("YELP ID REDONE", yelp_id)

                if yelp_id is None:

                    print("NONE")

                    url = "https://api.yelp.com/v3/businesses/{}".format(alias)
                    response = requests.get(url, headers=headers)
                    yelp_id = response.json()
                    
                    print(yelp_id.keys())

                    if 'id' in yelp_id.keys():
                        yelp_id = yelp_id['id']

                    else:
                        print("error!  You're being redirected to the error page")
                        return redirect(url_for('error'))

                    print("YELP ID 1", yelp_id)

                    if yelp_id is None:

                        return redirect(url_for("error"))

                    conn.execute(LOOKUP_TABLE_INSERT_STRING, yelp_id , alias)
                    conn.commit()

                

                if yelp_id is None:

                    return redirect(url_for("error"))

                    
            else:
                return(redirect(url_for("error")))


            headers = {
                'yelp_business_id':yelp_id
            }
           
            conn.close()

            #yelp_id = yelp_id.strip()

            print("YELP ID ",yelp_id[0])
            
            print(url_for("reviews", business_id = yelp_id[0]))

            
            return redirect(url_for("reviews",business_id=yelp_id[0]))
            
        
    elif request.method == 'GET':
        
        return render_template('search.html')