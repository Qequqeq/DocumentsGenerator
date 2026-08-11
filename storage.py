from parser import parce_people_data, parce_org_data
import json
from pathlib import Path

_JOBS = {}
JOBS_DIR = Path("temp/jobs")

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

def save_job_data(job_id: str, job_data: dict) -> None:
    file_path = JOBS_DIR / f"{job_id}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(job_data, f, ensure_ascii=False, indent=2, default=str)
    _JOBS[job_id] = job_data

def load_job(job_id):
    return _JOBS[job_id]
