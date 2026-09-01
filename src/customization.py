import json
from pathlib import Path
from typing import Dict

CUSTOMIZATION_DIR = Path("customization")
CUSTOMIZATION_FILE = CUSTOMIZATION_DIR / "customizations.json"

DEFAULT_DEGREE_INFO: Dict[int, str] = {
    1: 'Пострадавшему не требуется оказание медицинской помощи в организациях здравоохранения (микроповреждение/микротравма) /травма, требующая оказания простых мер первой помощи (легкие ушибы, синяки и т.п.) / измененное функциональное состояние организма работника восстанавливается во время регламентированного отдыха или к началу следующего рабочего дня (смены)',
    2: 'Травма с необходимостью обращения за медицинской помощью в организацию здравоохранения с потерей трудоспособности не более 3 дней (легкий несчастный случай)/незначительное воздействие на организм работника, организм восстанавливается не более чем через 3 дня',
    3: 'Травмы, при которых необходимо доставить работника в организацию здравоохранения или требуется ее посещение с потерей трудоспособности до 30 дней (легкий несчастный случай)/либо проявляются начальные признаки профессионального(ых) заболевания(й)',
    4: 'Травмы, при которых наступает длительное расстройство здоровья (тяжелый несчастный случай) работника с временной потерей трудоспособности от 30 до 60 дней/заболевания требующие лечения в стационаре организации здравоохранения',
    5: 'Травма, повлекшая смерть работника(ов) (тяжелый несчастный случай со смертельным исходом, групповой несчастный случай со смертельным исходом)/заболевания с потерей трудоспособности, приведшая к постоянной инвалидности или профессиональному заболеванию (стойкая утрата трудоспособности)'
}

DEFAULT_CHANCE_INFO: Dict[int, str] = {
    1: 'Очень низкая (практически невозможно) (Событие появляется в среднем реже, чем 1 раз год до 1 раза в 10 лет или реже)',
    2: 'Низкая (маловероятно) (Событие появляется в среднем от 1 раза в месяц до 1 раза в год)',
    3: 'Средняя (возможно) (Событие появляется в среднем от 1 раза в неделю до 2 раз в месяц)',
    4: 'Высокая (Событие появляется в среднем от 1 раза в смену до 2 раз в неделю)',
    5: 'Очень высокая (крайне вероятно) (Событие появляется в среднем один и более раз в смену)'
}

DEFAULT_COEFF_INFO: Dict[float, str] = {
    0.1: 'Крайне редко (Менее 10% рабочего времени)',
    0.3: 'Редко (От 10% до 25% рабочего времени)',
    0.5: 'Периодически (От 25% до 50% рабочего времени)',
    0.7: 'Часто (От 50% до 75% рабочего времени)',
    0.9: 'Постоянно ( От 75% и более рабочего времени)'
}

DEFAULT_SUMMARY_INFO: Dict[float, str] = {
    9.9: 'E (Пренебрежительно малый риск)',
    14.9: 'D (Приемлемый (допустимый) риск)',
    19.9: 'C (Средний (существенный) риск)',
    24.9: 'B (Высокий риск)',
    25: 'A (Крайне высокий риск)'
}

DEFAULT_SUMMARY_INFO_APLICATION: Dict[float, str] = {
    4.6: 'E (Пренебрежительно малый риск)',
    9.2: 'D (Приемлемый (допустимый) риск)',
    13.8: 'C (Средний (существенный) риск)',
    18.7: 'B (Высокий риск)',
    22.5: 'A (Крайне высокий риск)'
}

DEFAULT_CONTROL_INFO: Dict[str, str] = {
    'E (Пренебрежительно малый риск)': 'Ослабленный контроль проводится с периодичностью 1 раз в 5 лет',
    'D (Приемлемый (допустимый) риск)': 'Нормальный контроль проводится с периодичностью 1 раз в 3 года',
    'C (Средний (существенный) риск)': 'Нормальный контроль проводится с периодичностью 1 раз в 3 года',
    'B (Высокий риск)': 'Усиленный контроль проводится 1 раз в год',
    'A (Крайне высокий риск)': 'Непрерывный контроль по специальному регламенту'
}

def _load_raw() -> dict:
    if CUSTOMIZATION_FILE.exists():
        try:
            with open(CUSTOMIZATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_raw(data: dict) -> None:
    CUSTOMIZATION_DIR.mkdir(parents=True, exist_ok=True)
    with open(CUSTOMIZATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_degree_info() -> Dict[int, str]:
    custom = _load_raw().get("DEGREE_INFO", {})
    result = dict(DEFAULT_DEGREE_INFO)
    for key, value in custom.items():
        result[int(key)] = value
    return result


def get_chance_info() -> Dict[int, str]:
    custom = _load_raw().get("CHANCE_INFO", {})
    result = dict(DEFAULT_CHANCE_INFO)
    for key, value in custom.items():
        result[int(key)] = value
    return result


def get_coeff_info() -> Dict[float, str]:
    custom = _load_raw().get("COEFF_INFO", {})
    result = dict(DEFAULT_COEFF_INFO)
    for key, value in custom.items():
        result[float(key)] = value
    return result


def get_summary_info_dict() -> Dict[float, str]:
    custom = _load_raw().get("SUMMARY_INFO", {})
    if custom:
        result = {}
        for key, value in custom.items():
            result[float(key)] = value
        return dict(sorted(result.items()))
    return dict(sorted(DEFAULT_SUMMARY_INFO.items()))


def get_summary_info_aplication_dict() -> Dict[float, str]:
    custom = _load_raw().get("SUMMARY_INFO_APLICATION", {})
    if custom:
        result = {}
        for key, value in custom.items():
            result[float(key)] = value
        return dict(sorted(result.items()))
    return dict(sorted(DEFAULT_SUMMARY_INFO_APLICATION.items()))


def get_control_info() -> Dict[str, str]:
    custom = _load_raw().get("CONTROL_INFO", {})
    result = dict(DEFAULT_CONTROL_INFO)
    for key, value in custom.items():
        result[key] = value
    return result


def get_summary_info(summary: float) -> str:
    info = get_summary_info_dict()
    keys = sorted(info.keys())
    for threshold in keys:
        if summary <= threshold:
            return info[threshold]
    return info[keys[-1]]


def get_summary_info_aplication(summary: float) -> str:
    info = get_summary_info_aplication_dict()
    keys = sorted(info.keys())
    for threshold in keys:
        if summary <= threshold:
            return info[threshold]
    return info[keys[-1]]



def save_customization_section(section: str, data: dict) -> None:
    raw = _load_raw()
    raw[section] = data
    _save_raw(raw)


def reset_all_customizations() -> None:
    if CUSTOMIZATION_FILE.exists():
        CUSTOMIZATION_FILE.unlink()