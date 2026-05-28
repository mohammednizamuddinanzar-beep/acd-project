PIPELINE SentimentFlow
DATASET reviews FROM 'reviews.csv'
MODEL sentiment_model TASK 'nlp'
TRAIN sentiment_model ON reviews EPOCHS 6
EVALUATE sentiment_model
LOG 'Sentiment model ready'
ENDPIPELINE
