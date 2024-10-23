# Create a virtual environment
python3 -m venv lambda-env
source lambda-env/bin/activate

rm -rf python
mkdir python
# pip install sagemaker -t python/
# pip install sagemaker[api,inference] -t python/
pip install -q sagemaker[inference] -t python/
find sagemaker_pkg/ -name "*.dist-info" -type d -exec rm -r {} +
find sagemaker_pkg/ -name "tests" -type d -exec rm -r {} +


sudo apt-get update
sudo apt-get install -y zip

zip -r sagemaker_layer.zip python/

aws lambda publish-layer-version \
  --layer-name sagemaker-layer \
  --zip-file fileb://sagemaker_layer.zip \
  --compatible-runtimes python3.8


