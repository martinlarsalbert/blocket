"""
Module that inhabits some methods to download cars from blocket.se

"""
#!/usr/bin/python3.6

from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import re
import pandas as pd
from collections import OrderedDict
import numpy as np
import os.path

import logging
from logging import handlers
import sys
log = logging.getLogger('')
log.setLevel(logging.INFO)
format = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(format)
log.addHandler(ch)
fh = handlers.RotatingFileHandler('blocket.log', maxBytes=(1048576*5), backupCount=7)
fh.setFormatter(format)
log.addHandler(fh)

import warnings
warnings.filterwarnings('ignore')


car_paths = OrderedDict()
#car_paths['kangoo'] = r'https://www.blocket.se/goteborg/bilar?cg=1020&w=1&st=s&ccco=1&ca=15&is=1&l=0&md=th&cb=30&cbl1=4' #Göteborg
car_paths['kangoo'] = r'https://www.blocket.se/goteborg/bilar?cg=1020&w=3&st=s&ccco=1&ca=15&is=1&l=0&md=th&cb=30&cbl1=4' #Hela sverige

#car_paths['berlingo'] = r'https://www.blocket.se/goteborg/bilar?cg=1020&w=1&st=s&ca=31&is=1&l=0&md=th&cb=7&cbl1=1' #Göteborg
car_paths['berlingo'] = r'https://www.blocket.se/goteborg/bilar?ca=15&w=3&st=s&cg=1020&cb=7&cbl1=1' #Hela sverige

#car_paths['partner'] = r'https://www.blocket.se/goteborg/bilar?ca=15&st=s&cg=1020&cb=27&cbl1=14'
#car_paths['caddy'] = r'https://www.blocket.se/goteborg/bilar?cg=1020&w=1&st=s&ccco=1&ca=15&is=1&l=0&md=th&cb=40&cbl1=2'


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e):
    """
    It is always a good idea to log errors.
    This function just prints them, but you can
    make it do anything.
    """
    print(e)


def clean_string(s):
    s_clean = s.replace('\n', '').replace('\t', '')
    return s_clean


def clean_string2(s):
    s_clean = clean_string(s).replace(' ', '')
    return s_clean


def clean_price(s):
    s_clean = clean_string(s)
    s_clean = s_clean.replace('kr', '').replace(' ', '')
    price = float(s_clean)
    return price


def find_id_from_href(href):
    result = re.search(pattern=r'(\d*).htm', string=href)
    id = int(result.groups(1)[0])
    return id


def parse_car(href):
    raw_html = simple_get(href)
    html = BeautifulSoup(raw_html, 'html.parser')

    header = html.find('h1')
    name = clean_string(header.text)

    item_details = html.find('div', attrs={'id': 'item_details'})
    items = item_details.find_all('dl', attrs={'class': 'col-xs-4'})

    data = pd.Series()
    for item in items:
        key = clean_string2(item.find('dt').text)
        value = clean_string2(item.find('dd').text)
        data[key] = value

    data['header'] = name
    data.name = find_id_from_href(href=href)

    price = html.find('div', attrs={'id': 'vi_price'})
    data['price'] = clean_price(price.text)

    return data


def get_cars(car_path, max_cars=None):
    next_page_href = car_path
    df_cars = pd.DataFrame()
    counter = 0

    while not next_page_href is None:

        raw_html = simple_get(url=next_page_href)
        html = BeautifulSoup(raw_html, 'html.parser')
        item_links = html.find_all('a', attrs={'class': 'item_link'})

        for item_link in item_links:

            if not max_cars is None:
                if counter > max_cars:
                    return df_cars

            try:
                s_car = parse_car(href=item_link['href']).copy()
            except AttributeError:
                continue
            else:
                df_cars = df_cars.append(s_car)

            counter += 1

        next_page = html.find('a', attrs={'class': 'page_nav'}, text='\n                Nästa sida »\n            ')
        if next_page is None:
            next_page_href = None
        else:
            next_page_href = r'https://www.blocket.se/goteborg/bilar' + next_page['href']

    return df_cars


def decode_miltal(s_miltal):
    parts = s_miltal.split('-')

    if len(parts) == 1:
        return float(parts[0])
    elif len(parts) == 2:
        return np.mean([float(parts[0]), float(parts[1])])
    else:
        raise ValueError()

def load_from_blocket():

    logging.info('\n\n____________ Starting to load from blocket.se  _____________')

    df_cars = pd.DataFrame()

    for car_type, car_path in car_paths.items():
        logging.info('Loading car type:%s from:%s' % (car_type,car_path))

        df_car_type_cars = get_cars(car_path=car_path)
        df_car_type_cars['car type'] = car_type
        df_cars = df_cars.append(df_car_type_cars)

    index = df_cars['Tillverkningsår'] == '-'
    df_cars.loc[index, 'Tillverkningsår'] = df_cars.loc[index, 'Modellår']

    df_cars['Miltal'] = df_cars['Miltal'].apply(func=decode_miltal)

    float_cols = ['Miltal', 'Modellår', 'Tillverkningsår']
    df_cars[float_cols] = df_cars[float_cols].astype(float)

    index = (df_cars['price'] > 2000)
    df_cars = df_cars.loc[index]

    logging.info('All cars have been succesfully loaded today')

    return df_cars

def combine_new_and_old(df_cars,file_path = 'cars.csv'):

    logging.info('Combining with old data...')

    try:
        old_cars = pd.read_csv(file_path, sep=';', index_col=0)
    except:
        pass
    else:
        df_cars = df_cars.combine_first(old_cars)

    return df_cars

def save(df_cars,file_path = 'cars.csv'):

    path = __file__
    directory = os.path.split(path)[0]
    save_path = os.path.join(directory,file_path)

    df_cars.to_csv(save_path, sep=';')
    logging.info('All data has been saved to:%s' % save_path)

if __name__ == '__main__':

    df_cars = load_from_blocket()
    df_cars = combine_new_and_old(df_cars=df_cars)
    save(df_cars)




