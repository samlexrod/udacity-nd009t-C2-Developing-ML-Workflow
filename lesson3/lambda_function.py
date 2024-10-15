def lambda_handler(event, context):
 
    # Connecto to service
    client = boto3.client("stepfunctions")

    definition = event["definition"]

    # Update existing state machine
    state_machine_arn = "arn:aws:states:us-east-1:002427974286:execution:workflow-stepfunction-processing:fa6701a7-ba4f-4420-b0f1-094055bb7d5e"
    client.update_state_machine(definition=definition, stateMachineArn=state_machine_arn) 
    
    # Give AWS time to register the defintion
    time.sleep(5)
    
    #todo
    client.start_execution(input='{}', name='LambdaExecution', stateMachineArn=state_machine_arn) 
    
    return {
        'statusCode': 200,
        'body': 'The step function has successfully launched!'
    }
