#/home/kniv/Документы/Николай/ПримерыИсходников/Люди.xlsx
#/home/kniv/Документы/Николай/ПримерыИсходников/Орга.xlsx

from models import *

import pandas as pd
import pathlib as path


def parce_people_data(person_path=''):
    if person_path == '':
        people_path = path.Path(input("Введите путь к людям: "))
    else:
        people_path = person_path

    df = pd.read_excel(people_path, header=0)
    df = df.dropna(how="all")[2::]

    numeric_cols = [0, 6, 7, 8, 9]
    defaults = [0, 1, 0, 0, 0]
    for i, col_idx in enumerate(numeric_cols):
        df.iloc[:, col_idx] = pd.to_numeric(
            df.iloc[:, col_idx], errors='coerce'
        ).fillna(defaults[i]).astype(int)

    workers: list[WorkName] = []
    positions : list[str] = []

    for _, row in df.iterrows():
        if str(row.iloc[1]).strip() not in positions:
            workers.append(
                WorkName(
                    position=str(row.iloc[1]).strip(),
                    full_names=[str(row.iloc[13]).strip()],
                    number_at_workplace=int(row.iloc[6]),
                    woman=int(row.iloc[7]),
                    minors=int(row.iloc[8]),
                    disabled=int(row.iloc[9]),
                    equipment=str(row.iloc[11]).strip(),
                    materials=str(row.iloc[12]).strip(),
                    ID=int(row.iloc[0]),
                    workerDangers = [],
                    workerTotal = 0.0,
                    summary_info = ''
                )
            )
            positions.append(str(row.iloc[1]).strip())
        else:
            for worker in workers:
                if worker.position == str(row.iloc[1]).strip():
                    worker.number_at_workplace += int(row.iloc[6])
                    worker.woman += int(row.iloc[7])
                    worker.minors += int(row.iloc[8])
                    worker.disabled += int(row.iloc[9])
                    worker.full_names.append(str(row.iloc[13]).strip())
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
    adres = get_val(9)

    leader_text = get_val(16)
    leader = find_worker_in_text(leader_text, workers_list)

    chairman_text = get_val(21)
    chairman = find_worker_in_text(chairman_text, workers_list)

    com_members = []
    current_row = 23
    max_rows = len(df)

    while current_row < max_rows:
        val_text = get_val(current_row)
        col0_text = str(df.iloc[current_row, 0])
        if (not pd.isna(col0_text) and any(x in col0_text for x in ["¹", "²", "3 –"])) or val_text == "":
            if "Члены Комиссии" not in col0_text and not pd.isna(df.iloc[current_row, 0]):
                break

        worker = find_worker_in_text(val_text, workers_list)
        if worker:
            com_members.append(worker)

        current_row += 1

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
        leader=leader,
        chairman=chairman,
        com_members=com_members,
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