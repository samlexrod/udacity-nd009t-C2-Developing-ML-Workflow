
###############################################
# Setp 1: invokeSconesUnlimitedImageCategorizer
# This lambda function is triggered by an S3 event and starts the Step Function

import json
import random
import boto3

def lambda_handler(event, context):

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    s3_key = event["Records"][0]["s3"]["object"]["key"]
    print(f"-> Processing key: {s3_key}")

    print("-> Setting up payload...")
    json_payload = json.dumps({
            "s3_bucket": bucket,
            "s3_key": event["Records"][0]["s3"]["object"]["key"]
        })

    # Initialize the Step Functions client
    sfn_client = boto3.client('stepfunctions')
    step_function_arn = 'arn:aws:states:us-east-1:002427974286:stateMachine:scones-unlimited-state-machine'


    # Start Step Function execution
    try:
        print("-> Invoking scones step function...")
        response = sfn_client.start_execution(
            stateMachineArn=step_function_arn,
            input=json_payload
        )
        
        # Print execution details
        execution_arn = response['executionArn']
        print(f"Step Function invoked successfully! Execution ARN: {execution_arn}")

        return {
            'statusCode': 200,
            'body': json.dumps('Step Function Started!')
        }

    except:
        return {
            'statusCode': 500,
            'body': 'Failed to run scones unlimited state machine!'
        }

############################
# Setp 2: serializeImageData
# This lambda function is triggered by the Step Function and serializes the image data

import json
import boto3
import base64

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """A function to serialize target data from S3"""
    
    # Get the s3 address from the Step Function event input
    key = event["s3_key"]
    bucket = event["s3_bucket"]
    
    # Download the data from s3 to /tmp/image.png
    s3.download_file(bucket, key, "/tmp/image.png")
    
    # We read the data from a file
    with open("/tmp/image.png", "rb") as f:
        image_data = base64.b64encode(f.read())

    # Pass the data back to the Step Function
    print("Event:", event.keys())
    return {
        'statusCode': 200,
        'body': {
            "image_data": image_data,
            "s3_bucket": bucket,
            "s3_key": key,
            "inferences": []
        }
    }

#########################
# Setp 3: imageClassifier
# This lambda function is triggered by the Step Function and classifies the image

import json
import boto3
import base64

test = False

# Fill this in with the name of your deployed model
ENDPOINT = "scones-unlimited-prod-ep"
REGION = "us-east-1"

def lambda_handler(event, context):

    # Decode the image data
    image = base64.b64decode(event["body"]["image_data"])

    # Create a boto3 client for runtime SageMaker
    sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=REGION)

    # Make a prediction call using boto3
    if test:
        inferences = json.dumps([0] + [0] * 4).encode('utf-8')
    else:
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=ENDPOINT,
            ContentType='image/png',
            Body=image
        )

        # Get the inference result from the response
        inferences = response['Body'].read()

    # We return the data back to the Step Function    
    return {
        'statusCode': 200,
        'body': {
            'inferences': inferences.decode('utf-8'),
            's3_bucket': event["body"]["s3_bucket"],
            's3_key': event["body"]["s3_key"],
        }
    }

#############################
# Step 4: lowConfidenceFilter
# This lambda function is triggered by the Step Function and filters out low confidence inferences
# I would turn this into a Lambda function that set the categories. E.g. (bicycle, motorcycle, unlabeled)
# But to keep the integrity of the project lambdas, I will categorize in the later step.

import json


THRESHOLD = .94


def lambda_handler(event, context):
    
    # Grab the inferences from the event
    body = event["body"]
    inferences = json.loads(body["inferences"])
    
    # Check if any values in our inferences are above THRESHOLD
    meets_threshold = any([float(x) >= THRESHOLD for x in inferences])
    
    # If our threshold is met, pass our data back out of the
    # Step Function, else, end the Step Function with an error
    if meets_threshold:
        pass
    else:
        raise Exception(json.dumps({
            "errorMessage": "Threshold not met",
            "s3_bucket": event["body"]["s3_bucket"],
            "s3_key": event["body"]["s3_key"]
        }))

    return {
        'statusCode': 200,
        'body': {
            'inferences': inferences,
            's3_bucket': event["body"]["s3_bucket"],
            's3_key': event["body"]["s3_key"],
        }
        
    }

########################
# Step 5a: moveToDatalake
# This lambda function is triggered by the Step Function and moves the data to the datalake
# into the appropriate category key

import boto3
import json

def lambda_handler(event, context):

    # Get the s3 address from the Step Function event input
    print("Event:", event)
    body = event["body"]
    bucket = body["s3_bucket"]
    source_s3_key = body["s3_key"]
    inferences = body["inferences"]

    # Readd category mapping file from S3
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key="projects/ml-workflow/landingzone/label_categories.json")
    category_mapping = json.loads(response['Body'].read().decode('utf-8'))

    def set_inference_label():
        # Find which index has the highest value
        max_inference_value = max(inferences)
        max_index = inferences.index(max_inference_value)

        return category_mapping["key_mapping"][str(max_index)]
    
    key_category = set_inference_label()

    try:

        # Copy the data from the raw bucket to the processed bucket
        copy_source = {
            'Bucket': bucket,
            'Key': source_s3_key
        }
        
        # Get file name from the source_s3_key
        file_name = source_s3_key.split("/")[-1]
        destination_key = f"projects/ml-workflow/landingzone/categorized_data/{key_category}/{file_name}"
        print(f"Copying {source_s3_key} to {destination_key}...")
        s3.copy(copy_source, bucket, destination_key)
        
        # Delete the data from the raw bucket
        print(f"Deleting {source_s3_key} from raw bucket...")
        s3.delete_object(Bucket=bucket, Key=source_s3_key)
        
        # Move any other file in the source folder to the processed folder
        print(f"Moving any other files in the source folder to the processed folder...")
        
    except Exception as e:
        raise Exception(f"Error moving data to datalake: {e}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data moved to datalake!')
    }


########################
# Step 5b: moveToUnknown
# This lambda function is triggered by the Step Function when the previous function fails due to not meeting threshold
# files are moved to the unknwon category for further inspection

import boto3
import json

def lambda_handler(event, context):

    # Get the s3 address from the Step Function event input
    print("Event:", event)
    error_cause = event["Cause"]
    error_message = json.loads(error_cause)["errorMessage"]
    error_message = json.loads(error_message)
    bucket = error_message["s3_bucket"]
    source_s3_key = error_message["s3_key"]

    try:
        s3 = boto3.client('s3')
        
        # Copy the data from the raw bucket to the processed bucket
        copy_source = {
            'Bucket': bucket,
            'Key': source_s3_key
        }
        
        # Get file name from the source_s3_key
        file_name = source_s3_key.split("/")[-1]
        destination_key = f"projects/ml-workflow/landingzone/categorized_data/unknown/{file_name}"
        print(f"Copying {source_s3_key} to {destination_key}...")
        s3.copy(copy_source, bucket, destination_key)
        
        # Delete the data from the raw bucket
        print(f"Deleting {source_s3_key} from raw bucket...")
        s3.delete_object(Bucket=bucket, Key=source_s3_key)
        
        # Move any other file in the source folder to the processed folder
        print(f"Moving any other files in the source folder to the processed folder...")
        
    except Exception as e:
        raise Exception(f"Error moving data to datalake: {e}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data moved to datalake!')
    }
