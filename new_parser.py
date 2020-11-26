import sys
import re
import argparse
import json
import time
from urllib.parse import urljoin

from requests_html import HTMLSession
from bs4 import BeautifulSoup

HH_URL = "https://ekaterinburg.hh.ru/search/vacancy"

parser = argparse.ArgumentParser()

parser.add_argument("vacancy", type=str, nargs="?", default="data scientist")
args = parser.parse_args()


def get_vacancies_pagelist(vacancy_name):
    """Подключиться к head hunter и считать основную страницу с вакансиями
    Аргументы:
        vacancy_name - строка, возможно с пробелами, название вакансии
    Возвращает:
        main_soup - объект BeautifulSoup дла последующей обработки
        session - сессия для дальнейшей передачи
    """
    print("Обрабатываю вакансию {} ...".format(vacancy_name))
    vacancy_name = "+".join(vacancy_name.split())

    session = HTMLSession()
    page = session.get(HH_URL, params={'text': vacancy_name})
    main_soup = BeautifulSoup(page.content, 'html.parser')

    return main_soup, session


def make_json(vacancies_list):
    print("Сохраняю вакансии в формате JSON ...")
    with open("vacancies.json", 'w') as f:
        json.dump(vacancies_list, f, ensure_ascii=False)


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


def vacancies_url_generator(main_soup, session):
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

    while main_soup:
        vacancies = main_soup.select('.HH-LinkModifier')
        for vacancy in vacancies:
            yield vacancy

        try:
            next_page_href = main_soup.select('.HH-Pager-Controls-Next')[0]['href']
            url = urljoin(HH_URL, next_page_href)
            page = session.get(url)
            main_soup = BeautifulSoup(page.content, 'html.parser')
        except:
            print("Закончили...")
            break


def get_tags_list(soup):
    """Извлечь из страницы с вакансией список ключевых навыков, указанных в вакансии"""
    spans = soup.select('.bloko-tag__section_text')
    tags = [span.get_text() for span in spans]
    return tags


def get_salary(soup):
    """Извлечь зарплату со страницы"""
    return soup.select('.vacancy-salary')[0].get_text()


def get_vac_name(soup):
    """Извлечь название вакансии"""
    return soup.select('h1.bloko-header-1')[0].get_text()


def get_vac_id(vac_url):
    """Извлечь ID вакансии"""
    pattern= re.compile('\d+')
    return re.search(pattern, vac_url)[0]


def get_exp(soup):
    """Извлечь требуемый опыт работы"""
    experience = soup.find('span', {'data-qa':'vacancy-experience'})
    return experience.get_text()


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


def get_company(soup):
    """Извлечь название компании"""
    company_name = soup.find('span', {'class':'bloko-section-header-2 bloko-section-header-2_lite'})
    return company_name.get_text()


def get_description(soup):
    """Извлечь текстовое описание вакансии"""
    non_branded = soup.find('div', {'data-qa':'vacancy-description'})
    branded = soup.find('div', {'class':'vacancy-section HH-VacancyBrandedDescription-DANGEROUS-HTML'})
    description = non_branded or branded
    return description.get_text()


def get_timestamp(soup):
    """Извлечь дату создания вакансии"""
    vac_timestamp = soup.find('p', class_="vacancy-creation-time")
    return vac_timestamp.get_text()


def get_vacancy_contents(vac_url, session):
    """Возвращает словарь из элементов описания вакансии
    Аргументы:
        vac_url (str) - адрес вакансии
        session (HTMLSession) - открытое соединение
    """
    # time.sleep(3)  #  чтобы нас не остановили боты сайта, подождём какое-то время
    vac_page = session.get(vac_url)
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


if args.vacancy is not None:
    main_soup, session = get_vacancies_pagelist(args.vacancy)
    total_vac = get_vac_num(main_soup)

    print("По этому запросу найдено вакансий: {}".format(total_vac))
    print("Обработать эти вакансии? y/[n]\n")
    parse_user_choice = input()
    if parse_user_choice.lower() not in ["y", "yes", "д", "да"]:
        sys.exit()
    for vacancy in vacancies_url_generator(main_soup, session):
        vacancy_contents = get_vacancy_contents(vacancy['href'], session)
        print(vacancy_contents)
        break
