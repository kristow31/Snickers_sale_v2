import os
import time
import requests
from PIL import Image
from loguru import logger
import telebot

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

URL_site = 'https://stage.snickers.ru/hungerithm'

logger.add('logs/debug.log', format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", level="DEBUG", rotation="1 MB", compression="zip")

config_file = "config.ini"

if not os.path.exists(config_file):
    with open(config_file, "w") as file:
        file.write(
            "TELEGRAM_TOKEN = 0\n"
            "TELEGRAM_CHAT_ID = 0\n"
            "rucaptcha_token = 0\n"
            "headless_chrome = 0\n"
            "path_chrome = chromedriver.exe\n"
            "procent = 60"
        )


def read_file(file_name):
    config = {}
    try:
        fh = open(file_name, "r")
        try:
            lines = fh.readlines()
            for l in lines:
                kv = l.strip().split(' = ')
                config[kv[0]] = kv[1]
        finally:
            fh.close()
    except IOError:
        print("Configuration file not found.")
    return config


CONFIG = read_file(config_file)

bot = telebot.TeleBot(CONFIG["TELEGRAM_TOKEN"], parse_mode="MarkdownV2")


def getQuotes():
    URL = f'{URL_site}/backend/api/getQuotes?start=0'
    html = requests.get(URL)
    with open('getQuotes.json', 'wb') as file:
        file.write(html.content)
    Quotes = html.json()['result']
    return Quotes[0]


def getAvailableProducts():
    URL = f'{URL_site}/backend/api/getAvailableProducts'
    html = requests.get(URL)
    logger.info("Status {}", html.status_code)
    if int(html.status_code) == 200:
        with open('getAvailableProducts.json', 'wb') as file:
            file.write(html.content)

        Quotes = html.json()['result']
        return Quotes

    return None


def getCoupon(product, recaptcha):
    URL = f'{URL_site}/backend/api/getCoupon'
    html = requests.post(URL, json={"product_id": product, "g-recaptcha-response": recaptcha})
    with open('getCoupon.json', 'wb') as file:
        file.write(html.content)
    Quotes = html.json()
    return Quotes


def recaptcha(sitekey):
    rucaptcha_token = CONFIG['rucaptcha_token']
    res = False
    html = requests.post(f'http://rucaptcha.com/in.php?key={rucaptcha_token}&method=userrecaptcha&googlekey={sitekey}&pageurl={URL_site}')
    if html.status_code != 200 or html.text.find('OK') == -1:
        logger.info(f"Не верный запрос {html.status_code} >> {html.text}")
    else:
        text = html.text.split('|')[1]
        html = requests.get(f'http://rucaptcha.com/res.php?key={rucaptcha_token}&action=get&id={text}')
        if html.status_code == 200 and html.text.find('OK|') != -1:
            res = html.text.split('|')[1]
        while res == False:
            html = requests.get(f'http://rucaptcha.com/res.php?key={rucaptcha_token}&action=get&id={text}')
            if html.status_code == 200 and html.text.find('OK|') != -1:
                res = html.text.split('|')[1]
            logger.info(f"sitekey status {html.status_code} >> {html.text}")
            time.sleep(5)
    return res


def crop_center(pil_img, crop_width: int, crop_height: int) -> Image:
    """
    Функция для обрезки изображения по центру.
    """
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def screen(url, product_id):
    # options
    options = webdriver.ChromeOptions()
    options.add_argument( "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36")
    options.headless = bool(CONFIG['headless_chrome'])
    driver = webdriver.Chrome(
        executable_path=CONFIG['path_chrome'],
        options=options
    )

    driver.get(url)
    time.sleep(2)

    el = '//div[@id="age-modal"]//a[@href="#"]'
    try:
        WebDriverWait(driver, 5).until(ec.visibility_of_element_located((By.XPATH, el)))
        driver.find_element_by_xpath(el).click()
    except:
        pass

    el = '//button[@id="onetrust-accept-btn-handler"]'
    try:
        WebDriverWait(driver, 5).until(ec.visibility_of_element_located((By.XPATH, el)))
        driver.find_element_by_xpath(el).click()
    except:
        pass

    time.sleep(2)
    driver.save_screenshot(f'code_{product_id}_.png')
    print("Screen good")
    driver.close()
    driver.quit()
    fullImg = Image.open(f'code_{product_id}_.png')
    cropImg = crop_center(fullImg, 500, 600)
    cropImg.save(f'code__{product_id}.png')


def send_photo_telegram_old(product_id, name, url_coupon):
    try:
        files = {'photo': open(f'code__{product_id}.png', 'rb')}
        caption = f'''
{name}
{url_coupon}
'''
        token = CONFIG["TELEGRAM_TOKEN"]
        chat_id = CONFIG["TELEGRAM_CHAT_ID"]
        requests.post(f"https://api.telegram.org/bot{token}/sendPhoto?chat_id={chat_id}&caption={caption}", files=files)
    except:
        pass


def send_photo_telegram(product_id, name, url_coupon):
    photo = open(f'code__{product_id}.png', 'rb')
    caption = '''
*text*
[ссылка на код](http://www.example.com/)
    '''
    caption = caption.replace('text', name).replace('http://www.example.com/', url_coupon)
    bot.send_photo(CONFIG["TELEGRAM_CHAT_ID"], photo, caption=caption)


if __name__ == '__main__':

    logger.error('-------- START ----------')

    while True:

        while True:
            Products = getAvailableProducts()
            if not Products:
                logger.error("Ошибка сервера! Стоп программа")
                exit()

            ln = len(Products)
            logger.info('LEN = {}', ln)
            new = []
            for prod in Products:
                #logger.info(f"{prod=}")

                w = int(prod['weight'].split()[0].split('.')[0])
                if w > 70:
                    new.append(prod)
                    logger.debug(f"{prod['id']} | {prod['name']} {prod['weight']}")

            Products = new
            ln = len(Products)
            logger.info('NEW LEN = {}', ln)

            if ln > 0:
                break

            time.sleep(5)

        Quote = getQuotes()
        Quote['post'] = ''
        logger.info(f"{Quote=}")
        if int(Quote['value']) >= int(CONFIG['procent']):
            logger.info(f" > {CONFIG['procent']}")
            for prod in Products:
                logger.debug(f"{prod['id']} | {prod['name']} {prod['weight']}")
                cap = recaptcha("6LfLmLgUAAAAAAORbJmnPfTazf2wj1bhIFyFRHSi")
                # {'error': 0, 'result': {'id': 'a73e6a006fe9cbf4c29ea31f463affb6', 'date': '12.10.2021 14:00', 'time': 1634036400, 'timeslot': '202110121400', 'code': 'N105419634155886613', 'value': 20, 'currentSum': 0}}
                result = getCoupon(int(prod['id']), cap)
                logger.debug(f"{result=}")
                if int(result['error']) == 0:
                    url_coupon = "https://snickers.ru/hungerithm/#coupon/" + result['result']['id']
                    logger.debug(f"{url_coupon=}")
                    screen(url_coupon, int(prod['id']))
                    send_photo_telegram(int(prod['id']), f"{prod['name']} {prod['weight']}", url_coupon)
                    caption = '''
                    *text*
                    [ссылка на код](http://www.example.com/)
                        '''
                    caption = caption.replace('text', f"{prod['name']} {prod['weight']}").replace('http://www.example.com/', url_coupon)
                    bot.send_message(chat_id=CONFIG['TELEGRAM_CHAT_ID'], text=caption)
            time.sleep(2)
        time.sleep(10)
