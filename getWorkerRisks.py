from RisksAndDangers import *


def get_summary_info(summary):
    if summary <= 4.9:
        return SUMMARY_INFO[4.9]
    if summary <= 9.9:
        return SUMMARY_INFO[9.9]
    if summary <= 14.9:
        return SUMMARY_INFO[14.9]
    if summary <= 19.9:
        return SUMMARY_INFO[19.9]
    return SUMMARY_INFO[20.0]


def get_org_dangers(selected_danger_ids: list[int]) -> list[DangerTemplate]:
    for danger in DANGER_DATABASE.values():
        danger.active = danger.danger_number in selected_danger_ids
    return [danger for danger in DANGER_DATABASE.values() if danger.active]


def get_worker_risks(workName, org_dangers: list[DangerTemplate], risk_inputs: dict):
    # risk_inputs = {danger_number: {risk_number: {'deg': int, 'ch': int, 'kef': float}}}
    print(f'Оценка рисков работника {workName.position}')  # Keep for logs
    work_total = 0
    for danger in org_dangers:
        cur_risks = []
        sm = 0
        ttl = 0
        print(f'Опасность: {danger.danger_number}.{danger.danger_name}')  # Log
        for risk in danger.risks:
            print(f'Риск: {risk.risk_number}.{risk.risk_name}')  # Log
            danger_inputs = risk_inputs.get(danger.danger_number, {})
            risk_data = danger_inputs.get(risk.risk_number, {})
            deg = risk_data.get('deg', 0)
            if deg == 0: continue
            ch = risk_data.get('ch', 1)  # Default min
            kef = risk_data.get('kef', 0.1)  # Default min
            res = deg * ch * kef
            if res != 0:
                cur_risks.append(RiskTemplate(
                    risk_number = risk.risk_number,
                    risk_name = risk.risk_name,
                    degree = deg,
                    degree_info = DEGREE_INFO[deg],
                    chance = ch,
                    chance_info = CHANCE_INFO[ch],
                    coefficient = kef,
                    coefficient_info = COEFF_INFO[kef],
                    summary = res,
                    summary_info = get_summary_info(res),
                    danger_group_number = danger.danger_number,
                    danger_group_name = danger.danger_name,
                    control_periodic = risk.control_periodic,
                    management_measures = risk.management_measures
                ))
                sm += res
                ttl += res
        if len(cur_risks) != 0:
            cur_danger = DangerTemplate(
                danger_number = danger.danger_number,
                danger_name = danger.danger_name,
                summary = sm,
                risks = cur_risks
            )

            workName.workerDangers.append(cur_danger)
            work_total += ttl
    workName.workerTotal = work_total
    workName.summary_info = get_summary_info(work_total)