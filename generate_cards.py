from docxtpl import DocxTemplate
from getWorkerRisks import *
from RisksAndDangers import *
from pathlib import Path

def generate_worker_card(template_path, doc_date, org_data, workName, output_dir: Path = Path(".")):
    doc = DocxTemplate(template_path)
    danger_groups_list = []
    if workName.workerDangers:
        for danger_tpl in workName.workerDangers:
            items_list = []
            for risk_tpl in danger_tpl.risks:
                items_list.append({
                    "code": risk_tpl.risk_number,
                    "name": risk_tpl.risk_name,
                    "st": risk_tpl.degree,
                    "st_info": risk_tpl.degree_info,
                    "ch": risk_tpl.chance,
                    "ch_info": risk_tpl.chance_info,
                    "kef": str(risk_tpl.coefficient).replace('.', ','),
                    "kef_info": risk_tpl.coefficient_info,
                    "sum": f"{risk_tpl.summary:.1f}".replace('.', ','),
                    "total_let": f"{get_summary_info(summary=risk_tpl.summary)[:1]}",
                    "total_text": f"{get_summary_info(summary=risk_tpl.summary)[2:]}"
                })
            danger_groups_list.append({
                "group_id": danger_tpl.danger_number,
                "group_name": danger_tpl.danger_name,
                "group_score": f"{danger_tpl.summary:.1f}",
                "risk_list": items_list
            })
        comission = []
        for com_member in org_data.com_members:
            comission.append({
                "name": com_member.full_name
            })

        context = {
            'organizationName': org_data.full_name,
            'organizationAdres': org_data.adres,
            'organizationLead': org_data.leader.full_name,
            'INN': org_data.inn,
            'OKPO': org_data.okpo,
            'OKOGY': org_data.okogy,
            'OKVED': org_data.okved,
            'OKTMO': org_data.oktmo,
            'workNameID': workName.ID,
            'workNamePos': workName.position,
            'workNameNumber': workName.number_at_workplace,
            'workNameWoman': workName.woman,
            'workNameMinor': workName.minors,
            'workNameDisabled': workName.disabled,
            'equipment_list': [item.strip() for item in workName.equipment.split(',')] if workName.equipment else [],
            'materials_list': [item.strip() for item in workName.materials.split(',')] if workName.materials else [],
            'danger_groups': danger_groups_list,
            'TOTAL': f"{workName.workerTotal:.1f}".replace('.', ','),
            'com_chairman': org_data.chairman.full_name,
            'RiskKlass': workName.summary_info,
            'controlInfo': CONTROL_INFO[workName.summary_info],
            'documentDate': doc_date,
            'comission': comission,
            'division': workName.division
        }
        doc.render(context)
        doc.save(output_dir / f'Карта{workName.ID}{workName.position}.docx')


def generate_report(
        report_template_path: Path,
        output_dir: Path,
        org_data,
        people_data,
        doc_date: str
):
    doc = DocxTemplate(report_template_path)
    dangers_list = []
    for w in people_data:
        for d in w.workerDangers:
            risk_list = []
            for r in d.risks:
                if r.summary > 0:
                    risk_info = {
                        'number': r.risk_number,
                        'name': r.risk_name,
                        'fix': r.management_measures
                    }
                    if risk_info not in risk_list:
                        risk_list.append(risk_info)
            danger_info = {
                'group_id': d.danger_number,
                'group_name': d.danger_name,
                'risk_list': risk_list
            }
            if danger_info not in dangers_list:
                dangers_list.append({
                'group_id': d.danger_number,
                'group_name': d.danger_name,
                'risk_list': risk_list
            })


    first_table_context = {
        'totalWorkPlaces': 0,
        'totalWorkers': 0,
        'totalWoman': 0,
        'totalMinor': 0,
        'totalDisabled': 0,
        'totalE': 0,
        'totalWorkersE': 0,
        'totalWomanE': 0,
        'totalMinorE': 0,
        'totalDisabledE': 0,
        'totalD': 0,
        'totalWorkersD': 0,
        'totalWomanD': 0,
        'totalMinorD': 0,
        'totalDisabledD': 0,
        'totalC': 0,
        'totalWorkersC': 0,
        'totalWomanC': 0,
        'totalMinorC': 0,
        'totalDisabledC': 0,
        'totalB': 0,
        'totalWorkersB': 0,
        'totalWomanB': 0,
        'totalMinorB': 0,
        'totalDisabledB': 0,
        'totalA': 0,
        'totalWorkersA': 0,
        'totalWomanA': 0,
        'totalMinorA': 0,
        'totalDisabledA': 0
    }
    for worker in people_data:
        first_table_context['totalWorkPlaces'] += worker.number_at_workplace
        first_table_context['totalWorkers'] += worker.number_at_workplace
        first_table_context['totalWoman'] += worker.woman
        first_table_context['totalMinor'] += worker.minors
        first_table_context['totalDisabled'] += worker.disabled
        if worker.summary_info == 'E (Пренебрежительно малый риск)':
            first_table_context['totalWorkersE'] += worker.number_at_workplace
            first_table_context['totalWomanE'] += worker.woman
            first_table_context['totalMinorE'] += worker.minors
            first_table_context['totalDisabledE'] += worker.disabled
        if worker.summary_info == 'D (Приемлемый (допустимый) риск)':
            first_table_context['totalWorkersD'] += worker.number_at_workplace
            first_table_context['totalWomanD'] += worker.woman
            first_table_context['totalMinorD'] += worker.minors
            first_table_context['totalDisabledD'] += worker.disabled
        if worker.summary_info == 'C (Средний (существенный) риск)':
            first_table_context['totalWorkersC'] += worker.number_at_workplace
            first_table_context['totalWomanC'] += worker.woman
            first_table_context['totalMinorC'] += worker.minors
            first_table_context['totalDisabledC'] += worker.disabled
        if worker.summary_info == 'B (Высокий риск)':
            first_table_context['totalWorkersB'] += worker.number_at_workplace
            first_table_context['totalWomanB'] += worker.woman
            first_table_context['totalMinorB'] += worker.minors
            first_table_context['totalDisabledB'] += worker.disabled
        if worker.summary_info == 'A (Крайне высокий риск)':
            first_table_context['totalWorkersA'] += worker.number_at_workplace
            first_table_context['totalWomanA'] += worker.woman
            first_table_context['totalMinorA'] += worker.minors
            first_table_context['totalDisabledA'] += worker.disabled

    pos_summary = []
    for worker in people_data:
        full_control_info = CONTROL_INFO[worker.summary_info].split(" ")
        control_info = full_control_info[0] + " " + full_control_info[1]

        pos_summary.append({
            'num': worker.ID,
            'name': worker.position,
            'risk': worker.summary_info,
            'total': f"{worker.workerTotal:.1f}".replace('.', ','),
            'control_info': control_info,
            'div': worker.division
        })

    all_divisions = []
    for worker in people_data:
        if worker.division not in all_divisions:
            all_divisions.append(worker.division)

    divisions_summary = []
    for div in all_divisions:
        workers_in_div = [w for w in pos_summary if w['div'] == div]
        divisions_summary.append({
            'division': div,
            'workers': workers_in_div
        })

    comission = []
    for com_member in org_data.com_members:
        comission.append({
            "name": com_member.full_name
        })

    context = {
        'com_chairman': org_data.chairman.full_name,
        'organizationName': org_data.full_name,
        'organizationAdres': org_data.adres,
        'chairman_pos': org_data.chairman.position,
        'document_date': doc_date,
        'danger_groups': dangers_list,
        'totalWorkPlaces': first_table_context['totalWorkPlaces'],
        'divisions': all_divisions,
        'divisions_summary': divisions_summary,
        'comission': comission
    }
    context = context | first_table_context

    doc.render(context)

    report_path = output_dir / "Отчет.docx"
    doc.save(report_path)
    print("Сгенерирован полный отчет")
    return report_path