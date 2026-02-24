from models import *

import pandas as pd
import pathlib as path


def make_person(person_data):
    person_data = person_data.split()
    start_name_idx = 0
    while person_data[start_name_idx][0].upper() != person_data[start_name_idx][0]:
        start_name_idx += 1
    person_pos = ' '.join(person_data[:start_name_idx])
    person_name = ' '.join(person_data[start_name_idx:])
    return person_pos, person_name

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
        if str(row.iloc[0]) in alph:
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
            if str(row.iloc[1].strip()) not in positions:
                workers.append(
                    WorkName(
                        ID = worker_number,
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
                worker_number += 1
                positions.append(str(row.iloc[1].strip()))
            else:
                for worker in workers:
                    if worker.position == str(row.iloc[1]).strip():
                        worker.number_at_workplace += int(row.iloc[2])
                        worker.woman += int(row.iloc[3])
                        worker.minors += int(row.iloc[4])
                        worker.disabled += int(row.iloc[5])
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


def parce_org_data(org_path='', workers_list=None):
    if org_path == '':
        organization_path = path.Path(input("Введите путь к организации: "))
    else:
        organization_path = org_path

    df = pd.read_excel(organization_path, header=0)
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
    if chairman.full_name == chairmen[0].full_name:
        chairmen = chairmen[1:]

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