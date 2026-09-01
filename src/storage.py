from .parser import parce_people_data, parce_org_data
from .logger import log_info, log_error
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
        doc_date,
        org_df,
        people_df
):
    try:
        people_data = parce_people_data(people_path, people_df)
        org_data = parce_org_data(org_path, people_data, org_df)

        _JOBS[job_id] = {
            "card_template_path": card_template_path,
            "rep_template_path": rep_template_path,
            "people_path": people_path,
            "org_path": org_path,
            "doc_date": doc_date,
            "people_data": people_data,
            "org_data": org_data,
        }

        log_info("STORAGE", f"Создан новый проект {job_id}", {
            "workers_count": len(people_data),
            "org_name": org_data.full_name
        })
    except Exception as e:
        log_error("STORAGE", e, {"job_id": job_id, "action": "save_job"})
        raise


def save_job_data(job_id: str, job_data: dict) -> None:
    try:
        file_path = JOBS_DIR / f"{job_id}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2, default=str)
        _JOBS[job_id] = job_data

        log_info("STORAGE", f"Данные проекта {job_id} сохранены")
    except Exception as e:
        log_error("STORAGE", e, {"job_id": job_id, "action": "save_job_data"})
        raise


def load_job(job_id):
    try:
        if job_id not in _JOBS:
            raise KeyError(f"Job {job_id} not found")
        return _JOBS[job_id]
    except KeyError as e:
        log_error("STORAGE", e, {"job_id": job_id, "action": "load_job"})
        raise