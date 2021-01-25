import time
import os
import sys
import re
import argparse
import json
from urllib.parse import urljoin

from requests_html import HTMLSession
from bs4 import BeautifulSoup

HH_URL = "https://ekaterinburg.hh.ru/search/vacancy"

parser = argparse.ArgumentParser()

parser.add_argument("vacancy", type=str, nargs="?", default="data scientist")
parser.add_argument("-o", "--output", type=str, default="vacancies.json")
args = parser.parse_args()


def get_company(soup):
    """Извлечь название компании"""
    company_name = soup.find('span', {'class':'bloko-section-header-2 bloko-section-header-2_lite'})
    return company_name.get_text()


def get_contacts(soup):
    """Извлечь контакты рекрутера"""
    try:
        fio = soup.find('p', {'data-qa':'vacancy-contacts__fio'}).get_text()
    except: fio = ''
    try:
        phone = soup.find('p', {'data-qa':'vacancy-contacts__phone'}).get_text()
    except: phone = ''
    try:
        email = soup.find('a', {'data-qa':'vacancy-contacts__email'}).get_text()
    except: email = ''
    contacts_dict = dict(fio=fio, phone=phone, email=email)
    return contacts_dict


def get_description(soup):
    """Извлечь текстовое описание вакансии"""
    non_branded = soup.find('div', {'data-qa':'vacancy-description'})
    branded = soup.find('div', {'class':'vacancy-section HH-VacancyBrandedDescription-DANGEROUS-HTML'})
    description = non_branded or branded
    return description.get_text()


def get_exp(soup):
    """Извлечь требуемый опыт работы"""
    experience = soup.find('span', {'data-qa':'vacancy-experience'})
    return experience.get_text()


def get_salary(soup):
    """Извлечь зарплату со страницы"""
    return soup.select('.vacancy-salary')[0].get_text()


def get_tags_list(soup):
    """Извлечь из страницы с вакансией список ключевых навыков, указанных в вакансии"""
    spans = soup.select('.bloko-tag__section_text')
    tags = [span.get_text() for span in spans]
    return tags


def get_timestamp(soup):
    """Извлечь дату создания вакансии"""
    vac_timestamp = soup.find('p', class_="vacancy-creation-time")
    return vac_timestamp.get_text()


def get_vac_id(vac_url):
    """Извлечь ID вакансии"""
    pattern= re.compile('\d+')
    return re.search(pattern, vac_url)[0]


def get_vac_name(soup):
    """Извлечь название вакансии"""
    return soup.select('h1.bloko-header-1')[0].get_text()


def get_vac_num(soup):
    """Найти количество вакансий по указанному объекту soup и вернуть их число
    Аргументы:
        soup - объект BeautifulSoup
    Возвращает:
        int - число найденных вакансий
    """
    total_vac = soup.select('h1.bloko-header-1')[0]
    total_vac = total_vac.get_text()
    pattern = re.compile('\d+')
    s = re.findall(pattern, total_vac)
    if s:
        return int("".join(s))
    return 0


def get_vacancy_contents(vac_url, session):
    """Возвращает словарь из элементов описания вакансии
    Аргументы:
        vac_url (str) - адрес вакансии
        session (HTMLSession) - открытое соединение
    Возвращает:
        dict - словарь содержимого вакансии
    """
    # time.sleep(3)  #  чтобы нас не остановили боты сайта, подождём какое-то время
    vac_page = session.get(vac_url, timeout=3)
    soup = BeautifulSoup(vac_page.content, 'html.parser')

    vac_id = get_vac_id(vac_url)
    vac_name = get_vac_name(soup)
    company = get_company(soup)
    tags = get_tags_list(soup)
    salary = get_salary(soup)
    contacts = get_contacts(soup)
    fio = contacts['fio']
    phone = contacts['phone']
    email = contacts['email']
    exp = get_exp(soup)
    description = get_description(soup)
    timestamp = get_timestamp(soup)
    print("Обработана вакансия: {}".format(vac_name))

    return dict(
            vac_id=vac_id,
            vac_name=vac_name,
            company=company,
            tags=tags,
            salary=salary,
            fio=fio,
            phone=phone,
            email=email,
            exp=exp,
            description=description,
            timestamp=timestamp)


def get_vacancies_pagelist(vacancy_name):
    """Подключиться к head hunter и считать основную страницу с вакансиями
    Аргументы:
        vacancy_name - строка, возможно с пробелами, название вакансии
    Возвращает:
        main_soup - объект BeautifulSoup дла последующей обработки
        session - сессия для дальнейшей передачи
    """
    print("Обрабатываю вакансию {} ...".format(vacancy_name))

    session = HTMLSession()
    page = session.get(HH_URL, params={'text': vacancy_name})
    main_soup = BeautifulSoup(page.content, 'html.parser')

    return main_soup, session


def make_json(vacancy, filename):
    """Добавляет в указанный json-файл сериализованную строку vacancy
    Аргументы:
        vacancy (dict) - содержимое вакансии
        filename (str) - путь до файла, куда сохранять содержимое вакансии
    """
    with open(filename, 'a') as f:
        f.write(json.dumps(vacancy, ensure_ascii=False))
        f.write("\n")


def store_vacancy_name(vacancy_name):
    """ Сохранить наименование вакансии, которую обрабатываем в файл.
    Аргументы:
        vacancy_name (str) - наименование вакансии
    """
    with open("report_files/variables.tex", "w") as f:
        latex_command = "\\newcommand\\VacancyName{" + vacancy_name + "}\n"
        f.write(latex_command)


def store_vacancy_counts(num_vac_to_parse, total_vac):
    """ Сохранить в специально подготовленный файл LaTeX информацию о количестве
    вакансий на сайте и количестве вакансий, которые надо распарсить с помощью
    скрипта.
    Аргументы:
        num_vac_to_parse (int) - число вакансий, которые предоставляет сайт по
        данному запросу.
        total_vac (int) - число вакансий, которые нужно обработать.
    """
    with open("report_files/variables.tex", "a") as f:
        latex_command = "\\newcommand\\TotalVac{" + str(total_vac) + "}\n"
        f.write(latex_command)
        latex_command = "\\newcommand\\ParsedVac{" + str(num_vac_to_parse) + "}\n"
        f.write(latex_command)


def vacancies_url_generator(main_soup, session, num=-1):
    """Генератор, позволяющий получать по одной вакансии с указанной страницы.
    Генератор находит кнопку перехода на следующую страницу и пытается пройтись
    по всем вакансиям.

    Аргументы:
        main_soup - объект BeautifulSoup, с которого начинается поиск вакансий
        session - живое подключение

    Поставляет:
        vacancy (Tag) - тэг вакансии.
    """
    if session is None:
        session = HTMLSession()

    running_total = 0
    while main_soup and running_total < num:
        vacancies = main_soup.select('.HH-LinkModifier')
        for vacancy in vacancies:
            running_total += 1
            if running_total > num:
                print("Обработали указанное число вакансий")
                break
            yield vacancy

        try:
            next_page_href = main_soup.select('.HH-Pager-Controls-Next')[0]['href']
            url = urljoin(HH_URL, next_page_href)
            page = session.get(url)
            main_soup = BeautifulSoup(page.content, 'html.parser')
        except:
            print("Закончили...")
            break


def resolve_filename_conflicts(filename):
    """Разрешить конфликты названий файлов. Уточнить у пользователя, следует ли
    перезаписывать существующий файл.
    Аргументы:
        filename (str) - потенциально конфликтное имя файла.
    Возвращает:
        filename (str) - имя файла, утверждённое пользователем.
    """
    if os.path.exists(filename):
        print("\nФайл {} существует, перезаписываем? y/[n]".format(filename))
        overwrite_file = input()
        if overwrite_file.lower() not in ["y", "yes", "д", "да"]:
            print("\nВведите новое имя файла. Ему будет присвоен формат .json")
            filename = input() + '.json'
            filename = resolve_filename_conflicts(filename)
        os.remove(filename)
    return filename


if args.vacancy is not None:
    main_soup, session = get_vacancies_pagelist(args.vacancy)
    store_vacancy_name(args.vacancy)
    total_vac = get_vac_num(main_soup)
    print("По этому запросу найдено вакансий: {}".format(total_vac))

    print("\nСколько вакансий обрабатываем a(все)/число/c(отмена)? ")
    num_vac_to_parse = input()
    if num_vac_to_parse == 'c':
        print("Отменяю ...")
        sys.exit(1)
    elif num_vac_to_parse.isnumeric():
        num_vac_to_parse = int(num_vac_to_parse)
    else:
        num_vac_to_parse = total_vac
    print("\nБудет обработано {} вакансий, продолжаем? y/[n]".format(num_vac_to_parse))
    parse_user_choice = input()
    if parse_user_choice.lower() not in ["y", "yes", "д", "да"]:
        sys.exit(1)

    store_vacancy_counts(num_vac_to_parse, total_vac)
    filename = resolve_filename_conflicts(args.output)
    for vacancy in vacancies_url_generator(main_soup, session, num_vac_to_parse):
        try:
            vacancy_contents = get_vacancy_contents(vacancy['href'], session)
            make_json(vacancy_contents, filename)
        except KeyboardInterrupt:
            print("\nПарсинг досрочно прекращен пользователем.")
            break
        except AttributeError:
            print("\nОшибка чтения вакансии, либо доступ запрещён.")
            continue
