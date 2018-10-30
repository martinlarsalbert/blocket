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
car_paths['kangoo'] = r'https://www.blocket.se/hela_sverige?q=&cg=1020&w=3&st=s&ps=&pe=&mys=&mye=&ms=&me=&cxpf=&cxpt=&fu=&gb=&ccco=1&ca=15&is=1&l=0&md=th&cp=&cb=30&cbl1=4'
car_paths['berlingo'] = r'https://www.blocket.se/hela_sverige?q=&cg=1020&w=3&st=s&ps=&pe=&mys=&mye=&ms=&me=&cxpf=&cxpt=&fu=&gb=&ca=15&is=1&l=0&md=th&cp=&cb=7&cbl1=1'
car_paths['caddy'] = r'https://www.blocket.se/hela_sverige?q=&cg=1020&w=3&st=s&ps=&pe=&mys=&mye=&ms=&me=&cxpf=&cxpt=&fu=&gb=&ccco=1&ca=15&is=1&l=0&md=th&cp=&cb=40&cbl1=2'

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


def clean_horsepower(s_horsepower):
    result = re.search('\d+', s_horsepower)

    if result:
        return int(result.group(0))
    else:
        return np.nan


def get_extra_data(html):
    extra_data = html.find('dl', attrs={'class': 'col-xs-12 motor-extradata-details'})

    if extra_data:
        key_items = extra_data.findAll('dt')
        value_items = extra_data.findAll('dd')

        data_extra = pd.Series()

        for key_item, value_item in zip(key_items, value_items):
            key = key_item.text
            value = value_item.text
            data_extra[key] = value

        if 'Hästkrafter' in data_extra:
            s_horsepower = data_extra['Hästkrafter']
            data_extra['Hästkrafter'] = clean_horsepower(s_horsepower=s_horsepower)

        return data_extra

    else:
        return None

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

    price = html.find('div', attrs={'id': 'vi_price'})
    data['price'] = clean_price(price.text)

    extra_data = get_extra_data(html=html)
    if not extra_data is None:
        all_data = pd.concat([data,extra_data])
    else:
        all_data = data

    all_data.name = find_id_from_href(href=href)
    return all_data


def get_cars(car_path, max_cars=None):
    next_page_href = car_path
    df_cars = pd.DataFrame()
    counter = 0

    while not next_page_href is None:

        raw_html = simple_get(url=next_page_href)
        html = BeautifulSoup(raw_html, 'html.parser')
        item_list = html.find_all('div', attrs={'class': 'media-body desc'})

        for item in item_list:

            if not max_cars is None:
                if counter > max_cars:
                    return df_cars

            href = item.find('a', attrs={'class': 'item_link'}).get('href')

            try:
                s_car = parse_car(href=href).copy()
            except AttributeError:
                logging.warning('could not parse car:%s' % href)
                continue
            else:
                a = item.find('div', attrs={'class': 'pull-left'})
                place = a.contents[-1]
                s_car['place'] = place
                s_car['href'] = href
                df_cars = df_cars.append(s_car)

            counter += 1

        next_page = html.find('a', attrs={'class': 'page_nav'}, text='\n                Nästa sida »\n            ')
        if next_page is None:
            next_page_href = None
        else:
            next_page_href = r'https://www.blocket.se/hela_sverige' + next_page['href']

    return df_cars

def decode_miltal(s_miltal):
    if not isinstance(s_miltal,str):
        return np.nan

    parts = s_miltal.split('-')

    if len(parts) == 1:
        return float(parts[0])
    elif len(parts) == 2:
        return np.mean([float(parts[0]), float(parts[1])])
    else:
        raise ValueError()

def load_from_blocket(max_cars = None):

    logging.info('\n\n____________ Starting to load from blocket.se  _____________')

    df_cars = pd.DataFrame()

    for car_type, car_path in car_paths.items():
        logging.info('Loading car type:%s from:%s' % (car_type,car_path))

        df_car_type_cars = get_cars(car_path=car_path,max_cars=max_cars)
        df_car_type_cars['car type'] = car_type
        df_cars = df_cars.append(df_car_type_cars)

    index = df_cars['Tillverkningsår'] == '-'
    df_cars.loc[index, 'Tillverkningsår'] = df_cars.loc[index, 'Modellår']

    df_cars['Miltal'] = df_cars['Miltal'].apply(func=decode_miltal)
    index = df_cars['Miltal'].isnull()
    if index.sum() > 0:
        logging.warning('Missing "Miltal" removing cars: %s' % df_cars.loc[index]['header'])
        df_cars = df_cars.loc[~index]


    float_cols = ['Miltal', 'Modellår', 'Tillverkningsår']
    df_cars[float_cols] = df_cars[float_cols].astype(float)

    index = (df_cars['price'] > 2000)
    df_cars = df_cars.loc[index].copy()

    logging.info('%i cars have been succesfully loaded today' % len(df_cars))

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

    save_path_publish = os.path.join(directory, 'cars_publish.csv')

    df_cars.to_csv(save_path_publish, sep=',')
    logging.info('All data has also been saved to:%s' % save_path_publish)

if __name__ == '__main__':

    df_cars = load_from_blocket(max_cars=None)
    df_cars = combine_new_and_old(df_cars=df_cars)
    save(df_cars)




