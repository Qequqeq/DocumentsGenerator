import pandas as pd
from pathlib import Path
from typing import Tuple, List, Optional


def validate_org_file(file_path: Path) -> Tuple[bool, List[str], Optional[pd.DataFrame]]:
    errors = []
    try:
        df = pd.read_excel(file_path, header=0)
    except Exception as e:
        errors.append(
            f"Не удалось прочитать файл Excel: {str(e)}")
        return False, errors, None

    if df.shape[0] != 12:
        errors.append(
            f"Файл организации должен содержать 12 строк. Найдено {df.shape[0]} строк, смотрите шаблон.")
    if df.shape[1] != 3:
        errors.append(
            f"Файл организации должен содержать 3 столбца. Найдено {df.shape[1]} столбцов, смотрите шаблон.")
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
        1: "Полное наименование организации",
        2: "Сокращенное наименование организации",
        3: "Код причины постановки на учёт (КПП)",
        4: "Идентификационный номер налогоплательщика (ИНН)",
        5: "Код работодателя по ОКПО",
        6: "Код органа государственной власти по ОКОГУ",
        7: "Код основного вида экономической деятельности работодателя ОКВЭД",
        8: "Код территории по ОКТМО",
        9: "Юридический адрес организации",
        10: "Руководитель организации (должность, Ф.И.О. полностью)",
        11: "Председатель рабочей группы по проведению оценки профессиональных рисков (должность, Ф.И.О. полностью)",
        12: "Члены рабочей группы по проведению оценки профессиональных рисков (должность, Ф.И.О. полностью)"
    }
    for i, row in enumerate(df.itertuples(index=False)):
        expected_num = i + 1
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
                f"В строке {expected_num} название данных отсутствует (пустая ячейка). Ожидается: \"{expected_rows[expected_num]}\".")
            continue

        actual_name = str(row_name).strip()
        if actual_name != expected_rows[expected_num]:
            errors.append(
                f"Строка {expected_num}: ожидалось \"{expected_rows[expected_num]}\", получено \"{actual_name}\".")

    if errors:
        return False, errors, None

    return True, [], df