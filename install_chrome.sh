sudo apt update && sudo apt upgrade -y
sudo apt install -y libxss1 libappindicator1 libindicator7 unzip
sudo wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome*.deb
sudo apt install -y -f
google-chrome --version
rm -f google-chrome*.deb

# Search chrome driver: https://chromedriver.storage.googleapis.com/index.html

RESULT=$(google-chrome --version)
wget https://chromedriver.storage.googleapis.com/${RESULT:14:12}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
rm -f chromedriver_linux64.zip
