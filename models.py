from dataclasses import dataclass, field
from typing import List, Optional
from RisksAndDangers import *
@dataclass
class WorkName:
    ID: int  # номер в документе
    position: str # <<Генеральный директор>> и т.п.
    full_names: list[str]  # ФИО
    number_at_workplace: int # кол-во работников на месте
    woman: int # кол-во женщин
    minors: int # кол-во несовершеннолетних
    disabled: int # кол-во инвалидов
    equipment: str # <<ПЭВМ, оргтехника, ...>>
    materials: str # <<Припой, флюс, ...>>
    workerTotal: float
    summary_info: str  # описание итогового результат
    workerDangers: List[DangerTemplate] = field(default_factory=list) # все опасности (и риски) работника


@dataclass
class Organization:
    full_name: str # Полное наименование организации
    short_name: str # Сокращенное наименование организации
    kpp: str # Код причины постановки на учёт (КПП)
    inn: str # Идентификационный номер налогоплательщика (ИНН)
    okpo: str # Код работодателя по ОКПО2
    okogy: str # Код органа государственной власти по ОКОГУ2
    okved: str # Код основного вида экономической деятельности работодателя ОКВЭД2
    oktmo: str # Код территории по ОКТМО2
    adres: str # Юридический адрес организации
    leader: Optional[WorkName]  # Руководитель организации (должность, Ф.И.О. полностью)
    chairman: WorkName # Председатель комиссии по проведению специальной оценки условий труда (должность, ФИО полностью)
    com_members: List[WorkName] # Члены Комиссии по проведению СОУТ3 (должность, ФИО полностью)
    workers: List[WorkName] # Все сотрудники