PIPELINE FraudCheck
DATASET transactions FROM 'bank_data.csv'
MODEL fraud_net TASK 'classification'
TRAIN fraud_net ON transactions EPOCHS 8
PREDICT fraud_net INPUT 999 INTO fraud_score
DEPLOY fraud_net TO 'staging'
MONITOR fraud_net
LOG 'Fraud detection completed'
ENDPIPELINE
