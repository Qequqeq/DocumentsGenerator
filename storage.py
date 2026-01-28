from parser import parce_people_data, parce_org_data

_JOBS = {}


def save_job(
    job_id,
    card_template_path,
    rep_template_path,
    people_path,
    org_path,
    doc_date
):
    people_data = parce_people_data(people_path)
    org_data = parce_org_data(org_path, people_data)

    _JOBS[job_id] = {
        "card_template_path": card_template_path,
        "rep_template_path": rep_template_path,
        "people_path": people_path,
        "org_path": org_path,
        "doc_date": doc_date,
        "people_data": people_data,
        "org_data": org_data,
    }


def load_job(job_id):
    return _JOBS[job_id]
