from RisksAndDangers import *


def get_summary_info(summary):
    if summary <= 4.6:
        return SUMMARY_INFO[4.6]
    if summary <= 9.2:
        return SUMMARY_INFO[9.2]
    if summary <= 13.8:
        return SUMMARY_INFO[13.8]
    if summary <= 18.7:
        return SUMMARY_INFO[18.7]
    return SUMMARY_INFO[22.5]


def get_org_dangers(selected_danger_ids: list[int]) -> list[DangerTemplate]:
    for danger in DANGER_DATABASE.values():
        danger.active = danger.danger_number in selected_danger_ids
    return [danger for danger in DANGER_DATABASE.values() if danger.active]


def get_worker_risks(workName, org_dangers: list[DangerTemplate], risk_inputs: dict):
    # risk_inputs = {danger_number: {risk_number: {'deg': int, 'ch': int, 'kef': float}}}
    #print(f'Оценка рисков работника {workName.position}')
    work_total = 0
    for danger in org_dangers:
        cur_risks = []
        sm = 0
        ttl = 0
        #print(f'Опасность: {danger.danger_number}.{danger.danger_name}')
        for risk in danger.risks:
            #print(f'Риск: {risk.risk_number}.{risk.risk_name}')
            danger_inputs = risk_inputs.get(danger.danger_number, {})
            risk_data = danger_inputs.get(risk.risk_number, {})
            deg = risk_data.get('deg', 0)
            if deg == 0: continue
            ch = risk_data.get('ch', 1)
            kef = risk_data.get('kef', 0.1)
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