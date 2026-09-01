# -*- coding: utf-8 -*-
from models import *
import pandas as pd
import pathlib as path


def parce_people_data(person_path='', data_frame=pd.DataFrame()):
    df = None
    if data_frame.empty:
        if person_path == '':
            organization_path = path.Path(input("Введите путь к организации: "))
        else:
            organization_path = person_path

        df = pd.read_excel(organization_path, header=0)
    else:
        df = data_frame
    worker_number = 1

    df = df.fillna(int(0))

    workers: list[WorkName] = []
    positions: list[str] = []
    div = []
    level = []
    for _, row in df.iterrows():
        val = row.iloc[0]
        if row.iloc[1] == "Подразделение":
            if not level:
                level.append(float(row.iloc[0]))
                div.append(str(row.iloc[2]))
            else:
                while len(level) > 0 and level[-1] >= float(row.iloc[0]):
                    level = level[:-1]
                    div = div[:-1]

                div.append(str(row.iloc[2]))
                level.append(float(row.iloc[0]))
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
                    division=div[:],
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

    auditor_position = str(df.iloc[10, 1])
    auditor_fio = str(df.iloc[10, 2])

    auditor = Chairman(
        position=auditor_position,
        full_name=auditor_fio
    )

    leader_position = str(df.iloc[12, 1])
    leader_fio = str(df.iloc[12, 2])

    leader = Chairman(
        position=leader_position,
        full_name=leader_fio
    )

    chairman_position = str(df.iloc[14, 1])
    chairman_fio = str(df.iloc[14, 2])
    chairman = Chairman(
        position=chairman_position,
        full_name=chairman_fio
    )

    chairmen = []
    start_idx = 16
    col_position = 1
    col_name = 2

    while start_idx < len(df):
        pos = df.iloc[start_idx, col_position]
        name = df.iloc[start_idx, col_name]

        pos_empty = pd.isna(pos) or (isinstance(pos, str) and pos.strip() == "")
        name_empty = pd.isna(name) or (isinstance(name, str) and name.strip() == "")

        if pos_empty and name_empty:
            break
        chairmen.append(Chairman(
            position=str(pos) if not pos_empty else "",
            full_name=str(name) if not name_empty else ""
        ))
        start_idx += 1

    org = Organization(
        full_name=full_name,
        short_name=short_name,
        kpp=kpp,
        inn=inn,
        okpo=okpo,
        okogy=okogy,
        okved=okved,
        oktmo=oktmo,
        adres=adres,
        auditor=auditor,
        leader=leader,
        chairman=chairman,
        com_members=chairmen,
        workers=workers_list
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