sudo apt update && sudo apt upgrade -y
sudo apt install -y libxss1 libappindicator1 libindicator7
sudo wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome*.deb
sudo apt install -y -f
google-chrome --version

# Search chrome driver: https://chromedriver.storage.googleapis.com/index.html
