import json
import pandas as pd
from pandas import json_normalize
import numpy as np
import requests
import pprint
from tqdm import tqdm
from collections import Counter


DOMAIN = 'https://api.hh.ru/'

url = f'{DOMAIN}vacancies'

vacancy_name = 'Python'

# Создаём список куда будем загружать данные
result_all = []

# Создаём переменную с первоначальным номером страницы
page = 0
# Запускаем цикл
while True:
    try:
        # Генерируем параметры для get запроса
        params = {
            'text': f'NAME:({vacancy_name}) AND Москва',
            # страница
            'page': {page}
        }
        # print(params)

        # запускаем get запрос и сохраняем полученный результат в переменную
        result = requests.get(url, params=params).json()

        # сохраняем в отдельную переменную список с искомыми данными из результата
        items = result['items']

        # Добавляем список с искомыми данными в кумулятивный список
        result_all.extend(items)

        # увеличиваем номер страницы на один
        page += 1

        # переменная следующего номера страницы
        next_page = page + 1
        #  переменная общего количества страниц
        total_pages = result['pages']

        # проверяем болше ли номер следующей страницы общего количества страниц
        if next_page > total_pages:
            # если да - вызываем ошибку индексации
            raise IndexError
    # при ошибке индексации
    except IndexError:
        # выходим из цикла
        break

# Делаем копию выгрузки
result_all_without_dupl = result_all.copy()

# Создаём пустой список для занесения уникальных ID
id_list = []
# Создаём пустой список для занесения индекса дублированных ID
eliminate_position = []

# заполняем оба списка уникальных ID и индекса дублированных ID
for position in range(len(result_all_without_dupl)):
    interim_id = result_all_without_dupl[position]['id']
    if interim_id in id_list:
        eliminate_position.append(position)
    else:
        id_list.append(interim_id)

# Удаляем из копии выгрузки дублированные значения
for i in reversed(range(len(eliminate_position))):
    del result_all_without_dupl[eliminate_position[i]]

# сериализация json
json_object = json.dumps(result_all_without_dupl, indent=4, ensure_ascii=False)

# Записываем json объект в файл
with open("result_all_1.json", "w", encoding='utf-8') as outfile:
    outfile.write(json_object)

print(f'Длина копии ДО удаления дубликатов:     {len(result_all)}')
print(f'Длина копии ПОСЛЕ удаления дубликатов:  {len(result_all_without_dupl)}')

"""
Сколько всего вакансий
Средняя заработная плата
Все требования к данному типу вакансий
В скольких вакансиях указано данное требование (сортируем по убыванию)
"""

# 1 - Сколько всего вакансий
total_vacancies = f'1. Всего найдено {len(result_all)} вакансии.'
print(f'\n{total_vacancies}\n')

# 2 - Средняя заработная плата
# Создаём таблицу (DataFrame) из кумулятивного списка
df = pd.DataFrame(result_all)
# Оставляем в таблице только столбец с заработной платой (имеет вид словаря длиной 4)
df = df.loc[:, 'salary'].to_frame()
# Разворачиваем каждый элемент словаря в отдельный столбец
df = json_normalize(df['salary'])
# Удаляем все строки, в которых значения во всех столбцах None
df = df.dropna(how='all')
# Переиндексируем таблицу
df = df.reset_index(drop=True)
# Создаём отдельный столбец со средней ЗП Net
df['02_Ср_ЗП_net'] = np.where(df['gross'] == False, df[['from', 'to']].mean(axis=1), None)
# Создаём отдельный столбец со средней ЗП Gross
df['03_Ср_ЗП_gross'] = np.where(df['gross'] == True, df[['from', 'to']].mean(axis=1), None)
# Создаём отдельный столбец с количеством, если сумма указана в 'from' или 'to'
df['01_Количество'] = np.where(df['from'] > 0, 1, np.where(df['to'] > 0, 1, None))
# Создаём сводную таблицу
salary_pivot_table = pd.pivot_table(df, values=['01_Количество', '02_Ср_ЗП_net', '03_Ср_ЗП_gross'],
                                    index=['currency'],
                                    aggfunc={'01_Количество': np.sum,
                                             '02_Ср_ЗП_net': np.nanmean,
                                             '03_Ср_ЗП_gross': np.nanmean})
# Заменяем None на 0, и округляем значения сводной таблицы
salary_pivot_table = salary_pivot_table.fillna(0).astype('int')

print(f'2. Сводная таблица по заработной плате:\n\n {salary_pivot_table}\n')

# 3 - Все требования к данному типу вакансий
# Выборка hh.api не выдаёт запрашиваемых ключевых навыков по вакансии.
# Чтобы достать требуемые ключевые навыки, надо зайти в каждую выканасию.
# У hh.api есть ограничение по количеству итерируемых за раз страниц вакансий.

# Создаём пустой словарь
key_skills = {}

# Проходим по вакансиям с порогом 100 (чтобы избежать блокировки)
for item in tqdm(result_all[:101]):
    url = item['url']
    vacancy_id = item['id']

    result = requests.get(url).json()
    # записываем номер(ID) вакансии и её ключевые навыки
    key_skills[vacancy_id] = result['key_skills']

# Создаём список для всех уникальных требуемых ключевых навыках
skills_list = []
# Список всех запрашиваемых навыков
counter_skill = []

# Идём циклом по по словрю с требуемыми ключевыми навыками
for key, value in key_skills.items():
    interim_value_list = []

    if value is not []:
        for nested_dict in value:
            # записываем в переменную навык переводя его в нижний регистр,
            # чтобы избежать дубликатов из-за разного написания
            interim_value = nested_dict.get('name').lower()
            interim_value_list.append(interim_value)
            counter_skill.append(interim_value)
            # если навык ещё не встречался, записываем в список для уникальных
            if interim_value not in skills_list:
                skills_list.append(interim_value)
        key_skills[key] = interim_value_list

print(f'\n3. Все требования к данному типу вакансий:\n{skills_list}')

# Для презентации в консоли:
pd.options.display.float_format = '{:.2%}'.format

df_skills = pd.DataFrame(counter_skill, columns=['key_skills'])
df_skills['Количество'] = 1

df_skills = pd.DataFrame(
                         df_skills.groupby('key_skills')['Количество'].sum()
                        ).sort_values(by='Количество', ascending=False)

subtotal_qty = df_skills['Количество'].sum()

df_skills['Процент от общего числа навыков'] = df_skills["Количество"] / subtotal_qty

print(f'4. Сводная таблица анализа ключеввых навыков по позиции:\n\n {df_skills}\n')

# Для итогового файла:
skills_analysis = []
interim_skills_analysis = Counter(counter_skill)
subtotal_qty_2 = sum(interim_skills_analysis.values())
for key, value in interim_skills_analysis.items():
    skills_analysis.append({'01_name': key,
                            '02_count': value,
                            '03_percent': f'{value / subtotal_qty_2:.0%}'})

final_json = {
    '01 Keywords': vacancy_name,
    '02 Total Vacancies': len(result_all),
    '03 Average Salary': salary_pivot_table.to_dict(),
    '04 Vacancy Key Skills Requirements': skills_list,
    '05 Requested Key Skills Analysis': skills_analysis
}

print('5. Итоговый результат экспортируемый в json:\n')
pprint.pprint(final_json)

#  сериализация json
json_final_json = json.dumps(final_json, indent=4, ensure_ascii=False)
# Записываем json объект в файл
with open('final_json.json', 'w', encoding='utf-8') as f:
    f.write(json_final_json)
