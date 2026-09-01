# -*- coding: utf-8 -*-
from .RisksAndDangers import RiskTemplate, DangerTemplate, DANGER_DATABASE
from .customization import (
    get_degree_info,
    get_chance_info,
    get_coeff_info,
    get_summary_info,
    get_management_measures,

)


def get_org_dangers(selected_danger_ids: list[int]) -> list[DangerTemplate]:
    for danger in DANGER_DATABASE.values():
        danger.active = danger.danger_number in selected_danger_ids
    return [danger for danger in DANGER_DATABASE.values() if danger.active]


def get_worker_risks(workName, org_dangers: list[DangerTemplate], risk_inputs: dict):
    work_total = 0
    for danger in org_dangers:
        cur_risks = []
        sm = 0
        ttl = 0
        for risk in danger.risks:
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
                    degree_info = get_degree_info()[deg],
                    chance = ch,
                    chance_info = get_chance_info()[ch],
                    coefficient = kef,
                    coefficient_info = get_coeff_info()[kef],
                    summary = res,
                    summary_info = get_summary_info(res),
                    danger_group_number = danger.danger_number,
                    danger_group_name = danger.danger_name,
                    control_periodic = risk.control_periodic,
                    management_measures = get_management_measures(risk.risk_number, risk.management_measures)
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