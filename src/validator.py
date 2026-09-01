# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
from typing import Tuple, List, Optional
from datetime import datetime


def validate_org_file(file_path: Path) -> Tuple[bool, List[str], Optional[pd.DataFrame]]:
    errors = []
    try:
        df = pd.read_excel(file_path, header=0)
    except Exception as e:
        errors.append(
            f"Не удалось прочитать файл Excel: {str(e)}")
        return False, errors, None

    if df.shape[1] != 4:
        errors.append(
            f"Файл организации должен содержать 4 столбца. Найдено {df.shape[1]} столбцов, смотрите шаблон.")
    if errors:
        return False, errors, None

    expected_columns = ["№ п/п", "Наименование данных", "Данные организации"]
    for i, expected_col in enumerate(expected_columns):
        actual_col = str(df.columns[i]).strip()
        if actual_col != expected_col:
            errors.append(
                f"Название столбца {i + 1} не соответствует шаблону. Ожидается: \"{expected_col}\", найдено: \"{actual_col}\".")
    if errors:
        return False, errors, None

    expected_rows = {
        0: [1, 'Полное наименование организации'],
        1: [2, 'Сокращенное наименование организации'],
        2: [3, 'Код причины постановки на учёт (КПП)'],
        3: [4, 'Идентификационный номер налогоплательщика (ИНН)'],
        4: [5, 'Код работодателя по ОКПО'],
        5: [6, 'Код органа государственной власти по ОКОГУ'],
        6: [7, 'Код основного вида экономической деятельности работодателя ОКВЭД'],
        7: [8, 'Код территории по ОКТМО'],
        8: [9, 'Юридический адрес организации'],
        9: [10, 'Аудитор (должность, Ф.И.О. полностью)', 'Должность', 'Ф.И.О.'],
        11: [11, 'Руководитель организации (должность, Ф.И.О. полностью)', 'Должность', 'Ф.И.О.'],
        13: [12,
             'Председатель рабочей группы по проведению оценки профессиональных рисков (должность, Ф.И.О. полностью)',
             'Должность', 'Ф.И.О.'],
        15: [13, 'Члены рабочей группы по проведению оценки профессиональных рисков (должность, Ф.И.О. полностью)',
             'Должность', 'Ф.И.О.']
    }
    for i, row in enumerate(df.itertuples(index=False)):
        if i == 10 or i == 12 or i == 14 or i > 15: continue
        expected_num = expected_rows[i][0]
        expected_name = expected_rows[i][1]

        row_idx = row[0]
        row_name = row[1]

        try:
            actual_num = int(float(row_idx))
        except (ValueError, TypeError):
            errors.append(
                f"Ошибка в нумерации: в строке {expected_num} в столбце \"№ п/п\" найдено нечисловое значение: \"{row_idx}\".")
            continue

        if actual_num != expected_num:
            errors.append(f"Ошибка в нумерации: ожидался номер {expected_num}, найден {actual_num}.")

        if pd.isna(row_name):
            errors.append(
                f"В строке {expected_num} название данных отсутствует (пустая ячейка). Ожидается: \"{expected_rows[i][1]}\".")
            continue

        if row_name != expected_name:
            errors.append(
                f"В строке {expected_num} ожидалось \"{expected_rows[i][1]}\", найдено \"{row_name}\"."
            )

        if i > 8:
            dop_cols = [row[2], row[3]]
            for j in range(2):
                col = dop_cols[j]
                if pd.isna(col):
                    errors.append(
                        f"В строке {expected_num} отсутствует столбец для должности. Ожидается: \"{expected_rows[i][j + 2]}\"."
                    )
                if col != expected_rows[i][j + 2]:
                    errors.append(
                        f"Ошибка в строке {expected_num}: ожидался столбец: \"{expected_rows[i][j + 2]}\", найден \"{col}\"."
                    )
    if errors:
        return False, errors, None

    return True, [], df

def validate_people_file(file_path: Path) -> Tuple[bool, List[str], Optional[pd.DataFrame]]:
    errors = []
    try:
        df = pd.read_excel(file_path, header=0)
    except Exception as e:
        errors.append(
            f"Не удалось прочитать файл Excel: {str(e)}")
        return False, errors, None

    if df.shape[1] != 8:
        errors.append(
            f"Файл с сотрудниками должен содержать 8 столбцов. Найдено {df.shape[1]} столбцов, смотрите шаблон.")
    if errors:
        return False, errors, None

    expected_columns = [
        "№ п/п (№ рабочего места, по ранее проведенной СОУТ/АРМ))",
        "Наименование профессии или должности (специальности)",
        "Количество работающих на рабочем месте",
        "Из них женщин",
        "Из них несовершеннолетних",
        "Из них инвалидов",
        "Используемое оборудование",
        "Применяемые сырье и материалы"
    ]
    for i, expected_col in enumerate(expected_columns):
        actual_col = str(df.columns[i]).strip()
        if actual_col != expected_col:
            errors.append(f"Название столбца {i + 1} не соответствует шаблону. Ожидается: \"{expected_col}\", найдено: \"{actual_col}\".")
    if errors:
        return False, errors, None


    worker_ids = {}
    cur_number = 1
    last_div_level = 0
    for i, row in enumerate(df.itertuples(index=False)):
        cur_worker_id = row[0]
        if pd.isna(cur_worker_id):
            if isinstance(row[1], str):
                if cur_number in worker_ids and row[1] != "Подразделение":
                    print(row)
                    print(worker_ids)
                    errors.append(
                        f"Повторяется ID сотрудника \"{cur_number}\" в строках "
                        f"{worker_ids[cur_number] + 2} и {i + 2}."
                        f"Возможно, это вызвано смешиванием явной и неявной нумерации."
                    )
                else:
                    if row[1] != "Подразделение":
                        worker_ids[cur_number] = i
                cur_number += 1
                continue
        clean_id = str(cur_worker_id).strip()
        if not clean_id:
            continue
        if row[1] == "Подразделение":
            if not isinstance(clean_id, str):
                try:
                    c_id = float(clean_id)
                except Exception as e:
                    errors.append(
                        f"Неопознанный символ \"{clean_id}\" в маркере подразделения строки {i + 2}. "
                        f"Допускаются только маркеры-цифры"
                    )
            if int(float(clean_id)) != float(clean_id):
                errors.append(
                    f"Неопознанный символ \"{clean_id}\" в маркере подразделения строки {i + 2}. "
                    f"Допускаются только целочисленные маркеры"
                )
            if abs(last_div_level - int(float(clean_id))) > 1 and int(float(clean_id)) != 1:
                errors.append(
                    f"За подразделением с маркером {last_div_level} следует подразделение {row[1]} с маркером {int(float(clean_id))}."
                    f"Маркеры должны идти с шагом в единицу, либо быть 1 для подразделений верхнего уровня."
                )
            last_div_level = int(float(clean_id))
        else:
            try:
                worker_id = float(clean_id)
                if worker_id == int(worker_id):
                    worker_id = int(worker_id)
                if worker_id in worker_ids and row[1] != "Подразделение":
                    errors.append(
                        f"Повторяется ID сотрудника \"{worker_id}\" в строках "
                        f"{worker_ids[worker_id] + 2} и {i + 2}."
                        f"Возможно, это вызвано смешиванием явной и неявной нумерации."
                    )
                else:
                    if row[1] != "Подразделение":
                        worker_ids[worker_id] = i
            except (ValueError, TypeError):
                errors.append(
                    f"Некорректный ID сотрудника \"{cur_worker_id}\" в строке {i + 2}. "
                    f"Ожидается число или маркер подразделения (заглавные латинские буквы)."
                )

    if errors:
        return False, errors, None

    return True, [], df

def validate_date(date_str: str) -> Tuple[bool, Optional[str]]:
    if not date_str or not date_str.strip():
        return False, "Дата не может быть пустой."
    date_str = date_str.strip()

    try:
        parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
        current_year = datetime.now().year
        if parsed_date.year < 2000:
            return False, f"Год не может быть меньше 2000. Указан год: {parsed_date.year}."
        if parsed_date.year > current_year + 5:
            return False, f"Год не может быть больше {current_year + 5}. Указан год: {parsed_date.year}."

        return True, None
    except ValueError:
        return False, f"Неверный формат даты. Ожидается ДД.ММ.ГГГГ, вместо: \"{date_str}\"."