# Create a virtual environment
python3 -m venv lambda-env
source lambda-env/bin/activate

mkdir python
pip install sagemaker -t python/

zip -r sagemaker_layer.zip python/

# aws lambda publish-layer-version \
#   --layer-name sagemaker-layer \
#   --zip-file fileb://sagemaker_layer.zip \
#   --compatible-runtimes python3.8


