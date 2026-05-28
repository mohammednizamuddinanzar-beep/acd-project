# Intentional AI DSL errors
PIPELINE BrokenPipeline
MODEL anomaly_detector TASK 'anomaly-detection'
TRAIN anomaly_detector ON missing_dataset EPOCHS 5
ENDPIPELINE
