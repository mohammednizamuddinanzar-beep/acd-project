PIPELINE CustomerChurn
DATASET customers FROM 'data/customers.csv'
MODEL churn_model TASK 'classification'
SET epochs = 10
TRAIN churn_model ON customers EPOCHS 10
EVALUATE churn_model
PREDICT churn_model INPUT 3 INTO score
LOG 'Real CSV training pipeline completed'
ENDPIPELINE
