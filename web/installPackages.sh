#Install and run Mongo
sudo apt install software-properties-common dirmngr
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
sudo add-apt-repository 'deb http://repo.mongodb.org/apt/debian stretch/mongodb-org/4.0 main'
sudo apt update
sudo apt install mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
