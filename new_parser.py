import re
import argparse
import json
import time

from requests_html import HTMLSession
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser()

parser.add_argument("vacancy", type=str, nargs="?", default="data scientist")
args = parser.parse_args()


def get_vacancies_pagelist(vacancy_name):
    """Подключиться к head hunter и считать основную страницу с вакансиями
    Аргументы:
        vacancy_name - строка, возможно с пробелами, название вакансии
    Возвращает:
        main_soup - объект BeautifulSoup дла последующей обработки
    """
    print("Обрабатываю вакансию {} ...".format(vacancy_name))

    vacancy_name = "+".join(vacancy_name.split())
    url = "https://ekaterinburg.hh.ru/search/vacancy?text=" + vacancy_name

    session = HTMLSession()
    page = session.get(url)
    main_soup = BeautifulSoup(page.content, 'html.parser')

    return main_soup


    parse_user_choice = input()
    if parse_user_choice.lower() in ["y", "yes", "д", "да"]:
        print("Обрабатываю...")
        # Здесь проблема в том, что вакансии записываются в переменную только
        # после того, как список будет пройден. Это создаёт уязвимость в
        # направлении досрочного прекращения приложения. 
        vacancies = parse_vacancies(main, total_vac, session)
        print("Обработано вакансий: {}".format(len(vacancies)))
        print("Сохранить их в JSON-формате для последующей обработки? y/[n]")
        save_user_choice = input()
        if save_user_choice == "y":
            make_json(vacancies)
        else:
            print("Выхожу без сохранения")
    return


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


def vacancies_generator(main_soup):
    while main_soup:


def parse_vacancies(main, total_vac, session):
    """Процедура обработки списка вакансий, возвращает список словарей различных характеристик
    вакансий."""
    
    if session is None:
        session = HTMLSession()
    
    page_num = 1
    vacancies = []
    while main:
        print('Считываем страницу', page_num, '/', (int(total_vac) // 50)+1, '...')
        items = main.find_all('div', attrs = {'class':'vacancy-serp-item__info'})
        for item in items:
            vac_name = item.find('a', attrs={'class':'bloko-link HH-LinkModifier',
                                         'data-qa':'vacancy-serp__vacancy-title'})
            # пытаемся получить описание вакансии
            try:
                vacancy = get_vacancy_contents(vac_name['href'], session)
                vacancy['href'] = vac_name['href']
                vacancies.append(vacancy)
            except KeyboardInterrupt:
                print("Обработка досрочно прекращена пользователем")
                return vacancies
        try:
            next_page = main.find('a', attrs = {'class':'HH-Pager-Controls-Next'})
            url_next = "https://ekaterinburg.hh.ru" + next_page['href']
            time.sleep(3)
            page_num += 1
            page = session.get(url_next)
            main = BeautifulSoup(page.content, 'html.parser')
        except:
            print('Парсинг закончен')
            print('-------------------------')
            print('Всего вакансий:', total_vac)
            break
    return vacancies
    
    
def get_tags_list(soup):
    """Извлечь из страницы с вакансией список ключевых навыков, указанных в вакансии"""
    
    spans = soup.find_all('span', {'data-qa':'bloko-tag__text'})
    tags = [span.get_text() for span in spans]
    return tags


def get_salary(soup):
    """Извлечь зарплату со страницы"""
    
    salary = soup.find('p', {'class':'vacancy-salary'}).get_text()
    return salary


def get_vac_name(soup):
    """Извлечь название вакансии"""
    
    vac_name = soup.find('h1', attrs={'class':'bloko-header-1',
                                      'data-qa':'vacancy-title'})
    return vac_name.get_text()


def get_vac_id(soup):
    """Извлечь ID вакансии"""
    
    vac_id_source = soup.find('a', attrs={'class':'bloko-button bloko-button_secondary bloko-button_stretched',
                                          'data-qa':'vacancy-response-link-top'})
    pattern= re.compile('\d+')
    vac_id = re.search(pattern, vac_id_source['href'])[0]
    return vac_id


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
    """Возвращает словарь из элементов описания вакансии"""
    
    time.sleep(3)  #  чтобы нас не остановили боты сайта, подождём какое-то время
    vac_page = session.get(vac_url)
    soup = BeautifulSoup(vac_page.content, 'html.parser')
        
    vac_id = get_vac_id(soup)
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
    
    return dict(vac_id=vac_id, vac_name=vac_name, 
               company=company, tags=tags, salary=salary,
               fio=fio, phone=phone, email=email, exp=exp, 
               description=description, timestamp=timestamp)


if args.vacancy is not None:
    main_soup = get_vacancies_pagelist(args.vacancy)
    total_vac = get_vac_num(main_soup)
    print("По этому запросу найдено вакансий: {}".format(total_vac))
    print("Обработать эти вакансии? y/[n]\n")
