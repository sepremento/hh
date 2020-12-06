import locale
import json
import os
import re
import requests
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import pymorphy2 as pm

plt.rcParams.update({'figure.figsize': [12, 8]})
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8');


class KeyDict(defaultdict):
    """ Подкласс словаря, который по запросу к несуществующему ключу возвращает
    название ключа
    """
    def __missing__(self, key):
        return key


def create_raw_dataframe(json_file):
    """ Загрузить файл с информацией по вакансием и провести его предварительную
    обработку.
    Аргументы:
        json_file (str) - название .json файла, в котором содержится скачанная
        информация о вакансиях.
    Возвращает:
        raw (pandas.DataFrame) - предварительно обработанный датафрейм, с
        обработанными символами Юникода, форматом даты, понятным для pandas и
        нормализованным названием города.
    """
    morpher = pm.MorphAnalyzer()

    raw = pd.read_json('vacancies.json', lines=True)
    raw = raw.applymap(lambda s: unicodedata.normalize('NFKD', s) if type(s)==str else s)
    raw[['date', 'place']] = raw['timestamp'].str.extract('(\d+ \w+ \d+) в (.+)')
    raw = raw.drop('timestamp', axis=1)
    raw['date'] = pd.to_datetime(raw['date'], format="%d %B %Y")
    raw['place'] = [morpher.parse(s)[0].normal_form.title() for s in raw['place']]

    return raw


def plot_main_tags(vacancies_df, num=20):
    """ Отрисовать нужное количество самых популярных тэгов в вакансиях.
    Аргументы:
        vacancies_df (pandas.DataFrame) - датафрейм вакасий, желательно уже
        предобработанный (см. create_raw_dataframe)

        num (int) - количество тэгов, для которых нужно будет построить график.
        По умолчанию 20.
    """
    tags = [tag for tag_list in vacancies_df['tags'] for tag in tag_list]
    tags_counter = Counter(tags)

    plot_data = tags_counter.most_common(20)
    plot_data = [[x[0] for x in plot_data], [x[1] for x in plot_data]]

    plt.barh(y=plot_data[0], width=plot_data[1])
    plt.xlabel("Количество упоминаний тэга")
    plt.title("20 самых частых тэгов вакансий")
    plt.gca().invert_yaxis()
    plt.savefig("report_files/freq_tags.png", bbox_inches='tight')


def get_current_exchange_rates():
    """ Забраться на сайт 'free.currconv.com' и получить сегодняшние курсы
    валют.
    Возвращает:
        curr_dict (dict) - словарь курсов валют по отношению к рублю.
    """
    API_KEY = 'f57760a8c9133fde8b40'
    CUR_CODES = ['BYN', 'USD', 'EUR', 'KZT']
    URL = 'https://free.currconv.com/api/v7/convert'

    queries = ['_'.join((x, 'RUB')) for x in CUR_CODES]
    params = {'compact': 'ultra',
              'apiKey': API_KEY}

    cur_dict = {'RUB': 1}
    for query in queries:
        params.update({'q': query})
        resp = requests.get(URL, params=params)
        cur_dict.update(resp.json())
    cur_dict = {k[:3]: v for k,v in cur_dict.items()}

    return cur_dict


def serialize_exchange_rates(cur_dict):
    with open("report_files/xrates.json", "w") as f:
        json.dump(cur_dict, f)


def load_exchange_rates(json_file):
    cur_dict = {}
    with open(json_file, "r") as f:
        cur_dict = json.load(f)
    return cur_dict


def parse_xrates_bool():
    """ Если курсы валют свежие, то их можно и не обновлять """
    filename = 'report_files/xrates.json')
    if os.path.exists(filename):
        file_info = os.stat(filename)
        mtime = int(file_info.st_mtime)
        mtime = datetime.fromtimestamp(mtime)
        now = datetime.now
        if (now - mtime).days < 2:
            return False
    return True


def process_and_plot_salaries(vacancies_df):
    currencies = ['бел', 'USD', 'EUR', 'KZT', 'руб']
    cur_string='|'.join(currencies)
    pattern = '(от|до)((\d+)до(\d+)|\d+)({})'.format(cur_string)

    counts = raw['salary'].copy()
    counts = counts.str.replace(' ', '')
    counts = counts.str.extract(pattern).dropna(how='all')
    counts[1] = [x if x.isdigit() else None for x in counts[1]]
    counts[4] = counts[4].map(cur_to_code)
    counts[4] = counts[4].map(cur_dict)
    counts.iloc[:, 1:4] = counts.iloc[:,1:4].apply(pd.to_numeric)
    counts[2] = (counts[2] + counts[3]) / 2
    counts[1] = np.where(counts[0] == 'до', counts[1]/2, counts[1])
    counts[1] = counts[1].combine_first(counts[2])
    counts[1] = counts[1]*counts[4]
    counts = counts.drop([0,2,3,4], axis=1)
    counts = counts.rename(columns={1:'salary'})

    max_salary = max(counts['salary'])
    num = int(max_salary//50000)+1
    bins = np.linspace(0, max_salary, num=num)

    plt.hist(counts['salary'], bins=bins)
    plt.gca().set_xticks(bins)
    plt.xlabel("Зарплата, руб.")
    plt.ylabel("Количество вакансий")
    plt.title("Гистограмма зарплат")
    plt.savefig('report_files/salaries.png')


if __name__ == "__main__":
    # df = create_raw_dataframe('vacancies.json')
    # plot_main_tags(df)
    if parse_xrates_bool():
        cur_dict = get_current_exchange_rates()
        serialize_exchange_rates(cur_dict)
    else:
        cur_dict = load_exchange_rates('report_files/xrates.json')

