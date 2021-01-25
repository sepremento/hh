import locale
import json
import os
import re
import requests
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import urljoin
from tqdm import tqdm

import nltk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib import font_manager as fm

import pymorphy2 as pm
import warnings

warnings.filterwarnings('ignore')

font_dirs = ['./fonts/']
font_files = fm.findSystemFonts(fontpaths=font_dirs)
font_list = fm.createFontList(font_files)
fm.fontManager.ttflist.extend(font_list)

plt.rcParams['font.family'] = 'Roboto'
plt.rcParams['figure.figsize'] = [12, 8]
plt.rcParams.update({
    'axes.titlesize': 18,
    'axes.labelsize': 14,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14
    })

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8');


class KeyDict(defaultdict):
    """ Подкласс словаря, который по запросу к несуществующему ключу возвращает
    название ключа
    """
    def __missing__(self, key):
        return key


def create_raw_dataframe(json_file):
    """ Загрузить файл с информацией по вакансиям и провести его предварительную
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
    print("\nСоставляю датафрейм для обработки...", end="")

    raw = pd.read_json('vacancies.json', lines=True)
    raw = raw.applymap(lambda s: unicodedata.normalize('NFKD', s) if type(s)==str else s)
    raw[['date', 'place']] = raw['timestamp'].str.extract('(\d+ \w+ \d+) в (.+)')
    raw = raw.drop('timestamp', axis=1)
    raw['date'] = pd.to_datetime(raw['date'], format="%d %B %Y")
    raw['place'] = [morpher.parse(s)[0].normal_form.title() for s in raw['place']]
    print("Готово")
    return raw


def get_current_exchange_rates():
    """ Забраться на сайт 'free.currconv.com' и получить сегодняшние курсы
    валют.
    Возвращает:
        currency_dict (dict) - словарь курсов валют по отношению к рублю.
    """
    API_KEY = 'f57760a8c9133fde8b40'
    CUR_CODES = ['BYN', 'USD', 'EUR', 'KZT']
    URL = 'https://free.currconv.com/api/v7/convert'

    queries = ['_'.join((x, 'RUB')) for x in CUR_CODES]
    params = {'compact': 'ultra',
              'apiKey': API_KEY}

    currency_dict = {'RUB': 1}
    for query in queries:
        params.update({'q': query})
        resp = requests.get(URL, params=params)
        currency_dict.update(resp.json())
    currency_dict = {k[:3]: v for k,v in currency_dict.items()}

    return currency_dict


def get_salary_bins(max_salary):
    """ Получить количество разбиений в гистограмме зарплат для удобного чтения
    графика.
    Аргументы:
        max_salary (numeric) - максимальная зарплата в выборке
    Возвращает:
        шаг разбиения гистограммы.
    """
    if max_salary < 50001:
        return 10000
    else:
        return int(round(max_salary / 10, -4))


def get_xtick_step(max_xcount):
    """ Получить шаг подписей графика тэгов
    Аргументы:
        max_xcount (numeric) - максимальное количество упоминаний тэга, которое
        наблюдается в базе.
    """
    if max_xcount < 10:
        return 1
    else:
        return int(max_xcount / 10)


def beautify_plot(title, xlabel, ylabel):
    def decorator(plot_func):
        def wrapper():
            plt.clf()
            plot_func()
            plt.title(title)
            plt.gca().spines['right'].set_color('none')
            plt.gca().spines['top'].set_color('none')
            plt.gca().spines['left'].set_color('none')
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.tight_layout()
        return wrapper
    return decorator


@beautify_plot(title="20 самых частых тэгов вакансий",
        xlabel="Количество упоминаний тэга", ylabel="")
def plot_main_tags(vacancies_df, num=20):
    """ Отрисовать нужное количество самых популярных тэгов в вакансиях.
    Аргументы:
        vacancies_df (pandas.DataFrame) - датафрейм вакасий, желательно уже
        предобработанный (см. create_raw_dataframe)

        num (int) - количество тэгов, для которых нужно будет построить график.
        По умолчанию 20.
    """
    print("\nСоздаю график ключевых тэгов вакансии...", end="")
    tags = [tag for tag_list in vacancies_df['tags'] for tag in tag_list]
    tags_counter = Counter(tags)

    plot_data = tags_counter.most_common(20)
    plot_data = [[x[0] for x in plot_data], [x[1] for x in plot_data]]
    xstep = get_xtick_step(np.max(plot_data[1]))

    plt.barh(y=plot_data[0], width=plot_data[1], color='#87A96B')
    plt.xticks(np.arange(0, np.max(plot_data[1]), xstep), fontsize=14)
    plt.gca().invert_yaxis()
    plt.savefig("report_files/freq_tags.png")
    print("Готово")


def load_exchange_rates(json_file):
    cur_dict = {}
    with open(json_file, "r") as f:
        cur_dict = json.load(f)
    return cur_dict


def make_salary_statistics(salary_df):
    """ Сохранить основную статистику по зарплатам в специально подготовленный
    файл LaTeX.
    Аргументы:
        salary_df (pandas.DataFrame) - датафрейм с информацией о зарплатах, из
        которого нужно будет извлечь среднюю и медиану.
    """
    mean_salary = round(salary_df['salary'].mean(), 2)
    median_salary = round(salary_df['salary'].median(), 2)
    with open("report_files/variables.tex", "a") as f:
        latex_command = "\\newcommand\\MeanSalary{" + str(mean_salary) + "}\n"
        f.write(latex_command)
        latex_command = "\\newcommand\\MedianSalary{" + str(median_salary) + "}\n"
        f.write(latex_command)


def process_and_plot_salaries(vacancies_df, cur_dict):
    """ Обработка столбца заработных плат, приведение их к одной валюте,
    отрисовка гистограммы зарплат.
    Аргументы:
        vacancies_df (pandas.DataFrame) - датафрейм вакансий
        cur_dict (dict) - словарь курсов валют, полученный либо из файла, либо
        из Интернета.
    """
    print("\nСоздаю гистограмму зарплат...", end="")
    cur_to_code = KeyDict()
    cur_to_code.update({'бел': 'BYN', 'руб': 'RUB'})

    currencies = ['бел', 'USD', 'EUR', 'KZT', 'руб']
    cur_string='|'.join(currencies)
    pattern = '(от|до)((\d+)до(\d+)|\d+)({})'.format(cur_string)

    counts = df['salary'].copy()
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

    make_salary_statistics(counts)

    max_salary = max(counts['salary'])
    bin_step = get_salary_bins(max_salary)
    bins = np.arange(0, max_salary, bin_step)-(bin_step/2)*0.8

    plt.clf()
    plt.hist(counts['salary'], bins=bins, color='#87A96B', width=bin_step*0.8)
    plt.xticks(np.arange(0, max_salary, bin_step), fontsize=14)
    plt.yticks(fontsize=14)
    plt.xlim([-10000, np.max(bins)])
    plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.gca().spines['right'].set_color('none')
    plt.gca().spines['top'].set_color('none')
    plt.xlabel("Зарплата, руб.", fontsize=14)
    plt.ylabel("Количество вакансий", fontsize=14)
    plt.title("Гистограмма зарплат", fontsize=18, fontweight='bold')
    plt.tight_layout()
    plt.savefig('report_files/salaries.png')
    print("Готово")


def plot_keywords(vacancies_df, num=40):
    print("\nСоздаю график ключевых слов вакансий...")
    morpher = pm.MorphAnalyzer()

    stopwords_rus = nltk.corpus.stopwords.words('russian')
    stopwords_eng = nltk.corpus.stopwords.words('english')

    tokens = [nltk.word_tokenize(x, language='russian') for x in vacancies_df['description']]
    tokens = [token for tokens_list in tokens for token in tokens_list]
    tokens = [token.lower() for token in tokens if token.isalpha()]
    tokens = [morpher.parse(token)[0].normal_form for token in tqdm(tokens)]
    tokens = [token for token in tokens if token not in stopwords_rus]
    tokens = [token for token in tokens if token not in stopwords_eng]

    idx = nltk.text.ContextIndex(tokens)
    fdist = nltk.FreqDist(tokens)

    tags = [tag for tag_list in vacancies_df['tags'] for tag in tag_list]
    tags_counter = Counter(tags)
    keywords = [x[0].lower() for x in tags_counter.most_common(20)]

    similar = []
    for word in keywords:
        similar.append(idx.similar_words(word, n=100))
    similar = [word for wlist in similar for word in wlist]
    similar = [word for word in similar if re.match('[a-zа-я]+', word)]
    similar = list(set(similar))
    freqs = list(map(fdist.get, similar))

    top_words_df = pd.DataFrame(zip(similar, freqs), columns=['word', 'count'])
    top_words_df = top_words_df.sort_values('count', ascending=False)
    top_words_df = top_words_df.reset_index(drop=True)[:40]

    plt.clf()
    plt.figure(figsize=(12, 16))
    plt.barh(top_words_df['word'], top_words_df['count'], color='#87A96B')
    plt.yticks(fontsize=14)
    plt.xticks(fontsize=14)
    plt.gca().invert_yaxis()
    plt.gca().spines['right'].set_color('none')
    plt.gca().spines['top'].set_color('none')
    plt.gca().spines['left'].set_color('none')
    plt.title('Ключевые слова вакансий (англ.)', fontsize=18, fontweight='bold')
    plt.xlabel('Количество упоминаний', fontsize=14)
    plt.tight_layout()
    plt.savefig('report_files/keywords.png')
    print("Готово")


def plot_geography(vacancies_df):
    print("\nСоздаю график городов...", end="")
    cities = vacancies_df['place'].value_counts()[:15]

    plt.clf()
    plt.figure(figsize=(12,8))
    plt.barh(cities.index, cities, color='#87A96B')
    plt.gca().invert_yaxis()
    plt.gca().spines['top'].set_color('none')
    plt.gca().spines['right'].set_color('none')
    plt.gca().spines['left'].set_color('none')
    plt.xlabel('Количество вакансий', fontsize=14)
    plt.yticks(fontsize=14)
    plt.xticks(fontsize=14)
    plt.title('Распределение вакансий по городам', fontsize=18, fontweight='bold')
    plt.tight_layout()
    plt.savefig('report_files/geography.png')
    print("Готово")


def plot_vacancy_publish_dates(vacancies_df):
    print("\nСоздаю распределение по датам...", end="")
    dates = vacancies_df.groupby('date')['vac_id'].count().rename('count')

    plt.clf()
    plt.figure(figsize=(12,8))
    plt.plot(dates.index, dates, marker='o', color='#87A96B')
    plt.grid(ls='--')
    plt.gca().tick_params('x', labelrotation=45)
    plt.gca().spines['top'].set_color('none')
    plt.gca().spines['right'].set_color('none')
    plt.yticks(fontsize=14)
    plt.xticks(fontsize=14)
    plt.xlabel('Дата публикации', fontsize=14)
    plt.ylabel('Количество опубликованных вакансий', fontsize=14)
    plt.title('Распределение вакансий по дате публикации', fontsize=18, fontweight='bold')
    plt.tight_layout()
    plt.savefig('report_files/dates.png')
    print("Готово")


def serialize_exchange_rates(cur_dict):
    with open("report_files/xrates.json", "w") as f:
        json.dump(cur_dict, f)


def parse_xrates_bool():
    """ Если курсы валют свежие, то их можно и не обновлять """
    filename = 'report_files/xrates.json'
    if os.path.exists(filename):
        file_info = os.stat(filename)
        mtime = int(file_info.st_mtime)
        mtime = datetime.fromtimestamp(mtime)
        now = datetime.now()
        if (now - mtime).days < 2:
            return False
    return True


if __name__ == "__main__":
    if parse_xrates_bool():
        print("\nКурсы валют либо отсутствуют, либо старше двух дней. Скачиваю новые...")
        cur_dict = get_current_exchange_rates()
        serialize_exchange_rates(cur_dict)
    else:
        print("\nКурсы валют свежее двух дней, использую текущие курсы валют.")
        cur_dict = load_exchange_rates('report_files/xrates.json')
    df = create_raw_dataframe('vacancies.json')
    try:
        plot_main_tags(df)
        process_and_plot_salaries(df, cur_dict)
        # plot_keywords(df)
        plot_geography(df)
        plot_vacancy_publish_dates(df)
    except KeyboardInterrupt:
        print("Досрочно прекращено пользователем")

