# HeadHunter parser and analysis.
This is an utility for personal convenience. It parses hh.ru, analyzes the
vacancies and produces a report in pdf via LaTeX. The project is made up of two
python scripts, parser.py and analysis.py, one LaTeX document report.tex and a
little bash script to put them together.

## Usage
To get a report for python developer vacancies run:
```bash
./hh_project "python developer" tech
```

The `tech` keyword signals that the vacancies require a stack of technologies
and that report keywords would be mostly in english.

<hr>

Это небольшая утилита для собственного удобства. Она парсит сайт hh.ru на
предмет заданных вакансий, анализирует их и производит небольшой отчёт в .pdf
формате с помощью LaTeX. Проект состоит из двух скриптов на Python: parser.py и
analysis.py, одного LaTeX листинга report.tex и небольшого скрипта на bash,
чтобы свести всё воедино.

## Использование

Чтобы создать отчёт для, например, разработчика на Python, наберите в терминале:

```bash
./hh_project "python разработчик" tech
```

Ключевое слово `tech` обозначает, что у вакансии есть некоторый стек технологий,
а поэтому в список ключевых слов в отчёте нужно включать англоязычные слова.
Если анализируется вакансия, у которой такого стека технологий не
предполагается, например, врач, то это ключевое слово использовать не нужно.
