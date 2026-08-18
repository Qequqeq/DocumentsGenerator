# -*- coding: utf-8 -*-
from os.path import curdir

from models import *

import pandas as pd
import pathlib as path


def make_person(person_data):
    person_data = person_data.split("@")
    person_pos = person_data[0]
    person_name = person_data[1]
    return person_pos, person_name

def check_chairmen_text(arr):
    merged = []
    i = 0
    while i < len(arr):
        cur = arr[i].strip()
        if '@' in cur:
            merged.append(cur)
            i += 1
        else:
            combined = cur
            i += 1
            while i < len(arr) and '@' not in combined:
                combined += ', ' + arr[i].strip()
                i += 1
            merged.append(combined)
    return merged

def parce_people_data(person_path=''):
    worker_number = 1
    alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if person_path == '':
        people_path = path.Path(input("Введите путь к людям: "))
    else:
        people_path = person_path

    df = pd.read_excel(people_path, header=0)
    df = df.fillna(int(0))

    workers: list[WorkName] = []
    positions: list[str] = []
    div = []
    level = []
    for _, row in df.iterrows():
        val = row.iloc[0]
        if isinstance(val, str) and val in alph:
            if not level:
                level.append(str(row.iloc[0]))
                div.append(str(row.iloc[2]))
            else:
                while len(level) > 0 and ord(level[-1]) >= ord(str(row.iloc[0])):
                    level = level[:-1]
                    div = div[:-1]

                div.append(str(row.iloc[2]))
                level.append(str(row.iloc[0]))
        else:
            worker_id = None
            if pd.notna(val):
                if val == 0:
                    worker_id = worker_number
                    worker_number += 1
                else:
                    try:
                        if isinstance(val, str):
                            clean_val = val.strip()
                            if clean_val != '':
                                worker_id = float(clean_val)
                        else:
                            worker_id = float(val)
                    except (ValueError, TypeError):
                        pass
                    if worker_id == int(worker_id):
                        worker_id = int(worker_id)

            workers.append(
                WorkName(
                    ID = worker_id,
                    position= str(row.iloc[1].strip()),
                    division=div,
                    number_at_workplace=int(row.iloc[2]),
                    woman=int(row.iloc[3]),
                    minors=int(row.iloc[4]),
                    disabled=int(row.iloc[5]),
                    equipment=str(row.iloc[6]).strip(),
                    materials=str(row.iloc[7]).strip(),
                    workerDangers=[],
                    workerTotal=0.0,
                    summary_info=''
                )
            )
            positions.append(str(row.iloc[1].strip()))
    return workers

def find_worker_in_text(text: str, workers: List[WorkName]) -> Optional[WorkName]:
    if pd.isna(text) or text == "":
        return None

    text_lower = str(text).lower()
    for worker in workers:
        if not worker.full_names:
            continue

        name = worker.full_names[0]
        if name.lower() in text_lower:
            return worker

    return None


def parce_org_data(org_path='', workers_list=None, data_frame=pd.DataFrame()):
    df = None
    if data_frame.empty:
        if org_path == '':
            organization_path = path.Path(input("Введите путь к организации: "))
        else:
            organization_path = org_path

        df = pd.read_excel(organization_path, header=0)
    else:
        df = data_frame
    df = df.dropna(how="all")
    df.drop(df.columns[0], axis=1, inplace=True)
    def get_val(row_idx):
        val = df.iloc[row_idx, 1]
        if pd.isna(val):
            return ""
        return str(val).strip().replace('.0', '')

    full_name = get_val(0)
    short_name = get_val(1)
    kpp = get_val(2)
    inn = get_val(3)
    okpo = get_val(4)
    okogy = get_val(5)
    okved = get_val(6)
    oktmo = get_val(7)
    adres = get_val(8)

    leader_text = str(df.iloc[9, 1])
    chairman_text = str(df.iloc[10, 1])
    chairmen_text = str(df.iloc[11, 1]).split(',')
    chairmen_text = check_chairmen_text(chairmen_text)


    lead_typle = make_person(leader_text)
    leader = Chairman(
        position=lead_typle[0],
        full_name=lead_typle[1]
    )
    chairman_typle = make_person(chairman_text)
    chairman = Chairman(
        position=chairman_typle[0],
        full_name=chairman_typle[1]
    )


    chairmen_typle = []
    for man in chairmen_text:
        chairmen_typle.append(make_person(man))

    chairmen = []
    for tpl in chairmen_typle:
        chairmen.append(
            Chairman(
                position= tpl[0],
                full_name= tpl[1]
            )
        )

    org = Organization(
        full_name= full_name,
        short_name= short_name,
        kpp= kpp,
        inn= inn,
        okpo= okpo,
        okogy= okogy,
        okved= okved,
        oktmo= oktmo,
        adres= adres,
        leader = leader,
        chairman= chairman,
        com_members= chairmen,
        workers= workers_list
    )
    return org

def translit(word):
    converter = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',

    'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',

    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',

    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',

    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch',

    'ш': 'sh', 'щ': 'sch', 'ь': '', 'ы': 'y', 'ъ': '',

    'э': 'e', 'ю': 'yu', 'я': 'ya',

    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',

    'Е': 'E', 'Ё': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',

    'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',

    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',

    'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch',

    'Ш': 'Sh', 'Щ': 'Sch', 'Ь': '', 'Ы': 'Y', 'Ъ': '',

    'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'

}
    ans = ''
    for symb in word:
        if symb in converter.keys():
            ans += converter[symb]
        else:
            ans += symb
    return ans