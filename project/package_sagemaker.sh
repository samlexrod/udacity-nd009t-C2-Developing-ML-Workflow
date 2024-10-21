#!/bin/bash

# Create or Recreate the package directory
rm -rf lambda-sagemaker-package
mkdir -p lambda-sagemaker-package
cd lambda-sagemaker-package

# Create a virtual environment
python3 -m venv lambda-env
source lambda-env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the SageMaker SDK without dependencies
pip install sagemaker -t sagemaker_pkg/
find sagemaker_pkg/ -name "*.dist-info" -type d -exec rm -r {} +
find sagemaker_pkg/ -name "tests" -type d -exec rm -r {} +

# Create the initial ZIP package
zip -r9 lambda-sagemaker-package.zip sagemaker_pkg/

# Add the Lambda handler code to the ZIP
zip -g lambda-sagemaker-package.zip -j ../lambda_function.py

# Deactivate the virtual environment
deactivate
echo "Lambda package created: lambda-sagemaker-package.zip"
