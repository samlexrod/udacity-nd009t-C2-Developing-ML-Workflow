def lambda_handler(event, context):
        # The code to parse S3 event has provided to you, you only need to call the `preprocess` from the HelloBlazePreprocessLambda.py and return the status.
        import json
        import urllib
        
        for r in event['Records']:
                bucket = r['s3']['bucket']['name']
                key = urllib.parse.unquote_plus(r['s3']['object']['key'], encoding='utf-8')
                uri = "/".join([bucket, key])
        
        return {
                'statusCode': 200,
                'body': json.dumps('Hello from Lambda!')
        }
