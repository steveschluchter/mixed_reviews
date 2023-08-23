LOOKUP_TABLE_ALIAS_QUERY_STRING = "SELECT business_id FROM yelp_business_id_alias_lookup WHERE alias = (%s)"
#LOOKUP_TABLE_YELP_ID_QUERY_STRING = "SELECT business_id FROM yelp_business_id_alias_lookup WHERE id = '{}'" 
REVIEWS_TABLE_QUERY_STRING = "SELECT text FROM reviews where business_id = (%s)"
BUSINESS_TABLE_QUERY_STRING = "SELECT name, city, state from business WHERE business_id = (%s) LIMIT 1;"

LOOKUP_TABLE_INSERT_STRING = "INSERT INTO yelp_business_id_alias_lookup (business_id, alias) VALUES (%s,%s)"
REVIEWS_TABLE_INSERT_STRING = "INSERT INTO public.reviews (business_id, text, date) VALUES (%s, %s, %s)"

POSTGRESQL_CONNECTION_STRING="postgresql+psycopg2://postgres:JETPride75!@localhost:5432/postgres"