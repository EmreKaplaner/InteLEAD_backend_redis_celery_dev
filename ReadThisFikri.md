sudo apt-get update
sudo apt-get install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt #Path Adjustlarsın kanka
#### apt update
#### apt install docker.io -y
curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin docker-compose
#### chmod +x /usr/local/bin/docker-compose
#### chmod +x /root/InteLEAD_backend_redis_celery/start_backend.sh
### sudo apt-get update
### sudo apt-get install dos2unix
#### dos2unix start_backend.sh

TO START THE BACKEND: 
cd /root/InteLEAD_backend_redis_celery_dev
docker-compose up --build