# -*- coding: utf-8 -*-
from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)
from typing import List
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
import json
import shutil
import uuid
import os
import zipfile
from datetime import date
from src.generate_cards import *
from src.getWorkerRisks import get_org_dangers, get_worker_risks
from src.RisksAndDangers import DANGER_DATABASE
from src.customization import (
    get_degree_info,
    get_chance_info,
    get_coeff_info,
    get_summary_info_dict,
    get_summary_info_aplication_dict,
    get_control_info,
    get_management_measures,
    save_descriptions,
    save_ranges,
    save_management_measures,
    reset_descriptions,
    reset_ranges,
    reset_risks,
    DEFAULT_SUMMARY_INFO,
    DEFAULT_SUMMARY_INFO_APLICATION,
)
from src.RisksAndDangers import RISK_DATABASE
from src.storage import save_job, load_job
from src.parser import translit
import re
import io
from pathlib import Path
from src.validator import validate_org_file, validate_people_file, validate_date
from src.storage import save_job_data

router = APIRouter()

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("temp/uploads")
UPLOAD_DIR_SEC = Path("temp/jobs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_SEC.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('._')
    if not safe or safe == '.':
        safe = 'WorkerTemplate'
    if len(safe) > 100:
        safe = safe[:100]
    return safe


@router.get("/")
def main_menu(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/upload")
def upload_form(request: Request):
    default_date = date.today().strftime("%d.%m.%Y")
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "default_date": default_date
        }
    )

@router.get("/create-template")
def create_template_form(request: Request):
    all_dangers = list(DANGER_DATABASE.values())
    return templates.TemplateResponse(
        "create_template.html",
        {
            "request": request,
            "dangers": all_dangers,
            "degree_info": get_degree_info(),
            "chance_info": get_chance_info(),
            "coeff_info": get_coeff_info(),
            "existing": {}
        }
    )

@router.post("/create-template")
async def create_template(request: Request):
    form = await request.form()
    template_name = form.get("template_name", "").strip()
    template_name = translit(template_name)
    if not template_name:
        template_name = "JobTemplate"

    inputs = {}
    for key, value in form.items():
        if not value or '__' not in key:
            continue
        try:
            prefix, rest = key.split('__', 1)
            d_str, r_str = rest.split('__', 1)
            d_id = int(d_str)
            r_id = r_str
            val = value.strip()
            if not val:
                continue
            inputs.setdefault(d_id, {}).setdefault(r_id, {})
            if prefix == 'deg':
                inputs[d_id][r_id]['deg'] = int(val)
            elif prefix == 'ch':
                inputs[d_id][r_id]['ch'] = int(val)
            elif prefix == 'kef':
                inputs[d_id][r_id]['kef'] = float(val.replace(',', '.'))
        except Exception as e:
            print(f"Ошибка парсинга {key}: {e}")

    template_data = {
        "template_name": translit(template_name),
        "risks": inputs
    }
    json_str = json.dumps(template_data, ensure_ascii=False, indent=2)

    filename = f"{template_name}_template.json".replace(" ", "_")
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/upload_project")
async def upload_project(request: Request):
    default_date = date.today().strftime("%d.%m.%Y")
    return templates.TemplateResponse(
        "upload_project.html",
        {
            "request": request,
            "default_date": default_date
         }
    )


@router.post("/upload_project")
async def upload_project(
        request: Request,
        project_zip: UploadFile = File(...),
        doc_date: str = Form(...),
        card_template_file: UploadFile = File(...),
        rep_template_file: UploadFile = File(...),
        people_file: UploadFile = File(...),
        org_file: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    card_template_path = job_dir / "card_template.docx"
    rep_template_path = job_dir / "rep_template.docx"
    people_path = job_dir / "people.xlsx"
    org_path = job_dir / "org.xlsx"
    for upload, path in [
        (rep_template_file, rep_template_path),
        (card_template_file, card_template_path),
        (people_file, people_path),
        (org_file, org_path),
    ]:
        with open(path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

    is_date_valid, date_error = validate_date(doc_date)
    file_errors = []

    is_people_valid, people_errors, df_people = validate_people_file(people_path)
    if not is_people_valid:
        if people_path.exists():
            people_path.unlink()
        file_errors.extend(people_errors)

    is_org_valid, org_errors, df_org = validate_org_file(org_path)
    if not is_org_valid:
        if org_path.exists():
            org_path.unlink()
        file_errors.extend(org_errors)
    if not is_date_valid or file_errors:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "default_date": doc_date,
                "date_error": date_error,
                "file_errors": file_errors
            }
        )

    save_job(
        job_id=job_id,
        card_template_path=card_template_path,
        rep_template_path=rep_template_path,
        people_path=people_path,
        org_path=org_path,
        doc_date=doc_date,
        org_df=df_org,
        people_df=df_people
    )

    job = load_job(job_id)
    job["risk_inputs"] = {}
    job["org_dangers"] = []
    job["generated_cards"] = set()
    job = load_job(job_id)

    all_danger_ids = [DANGER_DATABASE[danger].danger_number for danger in DANGER_DATABASE.keys()]
    job["selected_danger_ids"] = all_danger_ids
    job["org_dangers"] = get_org_dangers(job["selected_danger_ids"])
    job["generated_cards"] = set()

    zip_content = await project_zip.read()
    if not zip_content:
        raise HTTPException(status_code=400, detail="ZIP-файл пуст")

    extract_dir = job_dir / "templates"
    extract_dir.mkdir(exist_ok=True)

    zip_path = job_dir / "project.zip"
    with open(zip_path, "wb") as f:
        f.write(zip_content)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    workers = job["people_data"]

    def find_worker(position):
        ans = []
        for w in workers:
            pos = w.position if hasattr(w, 'position') else w.get('position')
            if pos == position or pos.strip() == position.strip():
                ans.append(w)
        return ans

    def find_using_ID(ID):
        ans = []
        for w in workers:
            id = w.ID if hasattr(w, 'ID') else w.get('ID')
            if ID == id:
                ans.append(w)

    for json_file in extract_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                template_data = json.load(f)

            position = template_data.get("template_name")
            if not position:
                position = json_file.stem

            workersdd = find_worker(position)

            if not workersdd:
                print(f"Предупреждение: работник с должностью '{position}' не найден. Пропускаем.")
                continue

            for worker in workersdd:
                risks_data = template_data.get("risks", {})
                if not risks_data:
                    continue

                inputs = {}
                for d_key, r_dict in risks_data.items():
                    try:
                        d_id = int(d_key)
                    except ValueError:
                        try:
                            d_id = int(float(d_key))
                        except (ValueError, TypeError):
                            continue
                    inputs[d_id] = {}
                    for r_key, values in r_dict.items():
                        inputs[d_id][r_key] = {
                            "deg": values.get("deg", 1),
                            "ch": values.get("ch", 1),
                            "kef": values.get("kef", 0.0)
                        }


                job["risk_inputs"][position] = inputs
                job["risk_inputs"][worker.ID] = inputs

                output_dir = UPLOAD_DIR / job_id / "output"
                output_dir.mkdir(exist_ok=True)

                get_worker_risks(worker, job["org_dangers"], inputs)

                generate_worker_card(
                    template_path=job["card_template_path"],
                    doc_date=job["doc_date"],
                    org_data=job["org_data"],
                    workName=worker,
                    output_dir=output_dir
                )

                job["generated_cards"].add(worker.ID)

        except Exception as e:
            print(f"Ошибка при обработке файла {json_file}: {e}")
            continue
    for worker in workers:
        inputs = job["risk_inputs"].get(worker.ID)
        if inputs:
            get_worker_risks(worker, job["org_dangers"], inputs)
    shutil.rmtree(extract_dir, ignore_errors=True)
    if zip_path.exists():
        zip_path.unlink()
    save_job_data(job_id, job)

    return templates.TemplateResponse(
        "select_worker_risks.html",
        {
            "request": request,
            "workers": workers,
            "job_id": job_id,
            "risk_inputs": job.get("risk_inputs", {}),
            "generated_cards": job["generated_cards"]
        }
    )


@router.get("/select-dangers")
def show_select_dangers(request: Request, job_id: str):
    job = load_job(job_id)
    workers = job["people_data"]

    for worker in workers:
        inputs = job["risk_inputs"].get(worker.ID, {})
        if inputs:
            get_worker_risks(worker, job["org_dangers"], inputs)

    return templates.TemplateResponse(
        "select_worker_risks.html",
        {
            "request": request,
            "workers": workers,
            "job_id": job_id,
            "risk_inputs": job.get("risk_inputs", {}),
            "generated_cards": job.get("generated_cards", set())
        }
    )

@router.post("/upload")
async def upload_files(
    request: Request,
    doc_date: str = Form(...),
    card_template_file: UploadFile = File(...),
    rep_template_file: UploadFile = File(...),
    people_file: UploadFile = File(...),
    org_file: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    card_template_path = job_dir / "card_template.docx"
    rep_template_path = job_dir / "rep_template.docx"
    people_path = job_dir / "people.xlsx"
    org_path = job_dir / "org.xlsx"

    for upload, path in [
        (rep_template_file, rep_template_path),
        (card_template_file, card_template_path),
        (people_file, people_path),
        (org_file, org_path),
    ]:
        with open(path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

    is_date_valid, date_error = validate_date(doc_date)
    file_errors = []

    is_people_valid, people_errors, df_people = validate_people_file(people_path)
    if not is_people_valid:
        if people_path.exists():
            people_path.unlink()
        file_errors.extend(people_errors)

    is_org_valid, org_errors, df_org = validate_org_file(org_path)
    if not is_org_valid:
        if org_path.exists():
            org_path.unlink()
        file_errors.extend(org_errors)
    if not is_date_valid or file_errors:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "default_date": doc_date,
                "date_error": date_error,
                "file_errors": file_errors
            }
        )

    save_job(
        job_id=job_id,
        card_template_path=card_template_path,
        rep_template_path=rep_template_path,
        people_path=people_path,
        org_path=org_path,
        doc_date=doc_date,
        org_df = df_org,
        people_df=df_people
    )

    job = load_job(job_id)
    job["risk_inputs"] = {}
    job["org_dangers"] = []
    job["generated_cards"] = set()
    job = load_job(job_id)

    all_danger_ids = [DANGER_DATABASE[danger].danger_number for danger in DANGER_DATABASE.keys()]
    job["selected_danger_ids"] = all_danger_ids
    job["org_dangers"] = get_org_dangers(job["selected_danger_ids"])
    job["generated_cards"] = set()

    return templates.TemplateResponse(
        "select_worker_risks.html",
        {
            "request": request,
            "workers": job["people_data"],
            "job_id": job_id,
            "risk_inputs": job.get("risk_inputs", {}),
            "generated_cards": job["generated_cards"]
        }
    )

@router.post("/select-dangers")
async def select_dangers(
        request: Request,
        job_id: str = Form(...),
        danger_ids: List[int] = Form(default=[])
):
    job = load_job(job_id)

    all_danger_ids = [DANGER_DATABASE[danger].danger_number for danger in DANGER_DATABASE.keys()]

    job["selected_danger_ids"] = all_danger_ids

    job["org_dangers"] = get_org_dangers(job["selected_danger_ids"])

    job["generated_cards"] = set()
    job["risk_inputs"] = {}

    return templates.TemplateResponse(
        "select_worker_risks.html",
        {
            "request": request,
            "workers": job["people_data"],
            "job_id": job_id,
            "risk_inputs": job.get("risk_inputs", {}),
            "generated_cards": job["generated_cards"]
        }
    )


@router.get("/worker_risks/{job_id}/{worker_idx}")
def worker_risks_form(request: Request, job_id: str, worker_idx: int):
    job = load_job(job_id)
    workers = job["people_data"]
    if worker_idx < 0 or worker_idx >= len(workers):
        raise HTTPException(status_code=404, detail="Работник не найден")

    worker = workers[worker_idx]
    org_dangers = job["org_dangers"]
    saved_inputs = job["risk_inputs"].get(worker.ID, {})

    existing = {}
    for danger in org_dangers:
        danger_num = danger.danger_number
        existing[danger_num] = {}
        for risk in danger.risks:
            risk_num = risk.risk_number
            saved = saved_inputs.get(danger_num, {}).get(risk_num, {})

            risk_template = RISK_DATABASE.get(risk_num)
            if risk_template:
                default_deg = risk_template.degree
                default_ch = risk_template.chance
                default_kef = risk_template.coefficient
            else:
                default_deg = 1
                default_ch = 1
                default_kef = 0

            existing[danger_num][risk_num] = {
                "deg": saved.get("deg", default_deg),
                "ch": saved.get("ch", default_ch),
                "kef": saved.get("kef", default_kef)
            }

    return templates.TemplateResponse(
        "worker_risks.html",
        {
            "request": request,
            "job_id": job_id,
            "worker_idx": worker_idx,
            "worker": worker,
            "dangers": org_dangers,
            "existing": existing,
            "degree_info": get_degree_info(),
            "chance_info": get_chance_info(),
            "coeff_info": get_coeff_info()
        }
    )

@router.post("/save-as-template/{job_id}/{worker_idx}")
async def save_as_template(request: Request, job_id: str, worker_idx: int):
    job = load_job(job_id)
    workers = job["people_data"]
    if worker_idx < 0 or worker_idx >= len(workers):
        raise HTTPException(status_code=404, detail="Работник не найден")

    worker = workers[worker_idx]
    form = await request.form()

    inputs = {}
    for key, value in form.items():
        if not value or '__' not in key:
            continue
        try:
            prefix, rest = key.split('__', 1)
            d_str, r_str = rest.split('__', 1)
            d_id = int(d_str)
            r_id = r_str
            val = value.strip()
            if not val:
                continue
            inputs.setdefault(d_id, {}).setdefault(r_id, {})
            if prefix == 'deg':
                inputs[d_id][r_id]['deg'] = int(val)
            elif prefix == 'ch':
                inputs[d_id][r_id]['ch'] = int(val)
            elif prefix == 'kef':
                inputs[d_id][r_id]['kef'] = float(val.replace(',', '.'))
        except Exception as e:
            print(f"Ошибка парсинга {key}: {e}")

    template_data = {
        "template_name": safe_filename(translit(worker.position)).replace(" ", "_"),
        "worker_id": worker.ID,
        "risks": inputs
    }

    json_str = json.dumps(template_data, ensure_ascii=False, indent=2)
    filename = (f"{safe_filename(translit(worker.position))}_template.json").replace(" ", "_")

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/save_worker_risks/{job_id}/{worker_idx}")
async def save_worker_risks(request: Request, job_id: str, worker_idx: int):
    job = load_job(job_id)
    workers = job["people_data"]
    if worker_idx < 0 or worker_idx >= len(workers):
        raise HTTPException(status_code=404, detail="Работник не найден")

    worker = workers[worker_idx]
    form = await request.form()
    inputs = {}

    for key, value in form.items():
        if not value or '__' not in key:
            continue
        try:
            prefix, rest = key.split('__', 1)
            d_str, r_str = rest.split('__', 1)
            d_id = int(d_str)
            r_id = r_str
            val = value.strip()
            if not val:
                continue
            inputs.setdefault(d_id, {}).setdefault(r_id, {})
            if prefix == 'deg':
                inputs[d_id][r_id]['deg'] = int(val)
            elif prefix == 'ch':
                inputs[d_id][r_id]['ch'] = int(val)
            elif prefix == 'kef':
                inputs[d_id][r_id]['kef'] = float(val.replace(',', '.'))
        except Exception as e:
            print(f"Ошибка парсинга {key}: {e}")

    job["risk_inputs"][worker.ID] = inputs
    job["generated_cards"].add(worker.ID)

    output_dir = UPLOAD_DIR / job_id / "output"
    output_dir.mkdir(exist_ok=True)

    get_worker_risks(worker, job["org_dangers"], inputs)
    generate_worker_card(
        template_path=job["card_template_path"],
        doc_date=job["doc_date"],
        org_data=job["org_data"],
        workName=worker,
        output_dir=output_dir
    )

    print(f"Сгенерирована карта для: {worker.position}")
    save_job_data(job_id, job)
    return RedirectResponse(url=f"/select-dangers?job_id={job_id }", status_code=303)

@router.post("/apply-template/{job_id}/{worker_idx}")
async def apply_template(
    request: Request,
    job_id: str,
    worker_idx: int,
    template_file: UploadFile = File(...)
):
    job = load_job(job_id)
    workers = job["people_data"]
    if worker_idx < 0 or worker_idx >= len(workers):
        raise HTTPException(status_code=404, detail="Работник не найден")

    worker = workers[worker_idx]

    content = await template_file.read()
    try:
        template_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Некорректный JSON файл")

    risks_data = template_data.get("risks")
    if not isinstance(risks_data, dict):
        raise HTTPException(status_code=400, detail="Отсутствует поле 'risks'")

    inputs = {}
    for d_key, r_dict in risks_data.items():
        try:
            d_id = int(d_key)
        except ValueError:
            try:
                d_id = int(float(d_key))
            except (ValueError, TypeError):
                continue

        inputs[d_id] = {}
        for r_key, values in r_dict.items():
            inputs[d_id][r_key] = {
                "deg": values.get("deg", 1),
                "ch": values.get("ch", 1),
                "kef": values.get("kef", 0.0)
            }


    job["risk_inputs"][worker.ID] = inputs
    job["generated_cards"].add(worker.ID)
    get_worker_risks(worker, job["org_dangers"], inputs)
    output_dir = UPLOAD_DIR / job_id / "output"
    output_dir.mkdir(exist_ok=True)

    generate_worker_card(
        template_path=job["card_template_path"],
        doc_date=job["doc_date"],
        org_data=job["org_data"],
        workName=worker,
        output_dir=output_dir
    )

    job["generated_cards"].add(worker.ID)
    return RedirectResponse(url=f"/select-dangers?job_id={job_id}", status_code=303)


@router.post("/apply-template-bulk/{job_id}")
async def apply_template_bulk(
        request: Request,
        job_id: str,
        template_file: UploadFile = File(...),
        worker_indices: List[str] = Form(...)
):
    job = load_job(job_id)
    workers = job["people_data"]

    content = await template_file.read()
    try:
        template_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Некорректный JSON файл")

    risks_data = template_data.get("risks")
    if not isinstance(risks_data, dict):
        raise HTTPException(status_code=400, detail="Отсутствует поле 'risks'")

    inputs = {}
    for d_key, r_dict in risks_data.items():
        try:
            d_id = int(d_key)
        except ValueError:
            try:
                d_id = int(float(d_key))
            except (ValueError, TypeError):
                continue

        inputs[d_id] = {}
        for r_key, values in r_dict.items():
            inputs[d_id][r_key] = {
                "deg": values.get("deg", 1),
                "ch": values.get("ch", 1),
                "kef": values.get("kef", 0.0)
            }

    output_dir = UPLOAD_DIR / job_id / "output"
    output_dir.mkdir(exist_ok=True)

    applied_count = 0
    for idx_str in worker_indices:
        try:
            worker_idx = int(idx_str)
            if worker_idx < 0 or worker_idx >= len(workers):
                continue

            worker = workers[worker_idx]
            job["risk_inputs"][worker.ID] = inputs
            job["generated_cards"].add(worker.ID)
            get_worker_risks(worker, job["org_dangers"], inputs)

            generate_worker_card(
                template_path=job["card_template_path"],
                doc_date=job["doc_date"],
                org_data=job["org_data"],
                workName=worker,
                output_dir=output_dir
            )
            applied_count += 1
        except (ValueError, TypeError):
            continue

    save_job_data(job_id, job)

    return RedirectResponse(url=f"/select-dangers?job_id={job_id}", status_code=303)

def sanitize_filename(name: str) -> str:
    name = translit(name)
    return re.sub(r'[<>:"/\\|?*]', '_', name)

@router.get("/save-project/{job_id}")
async def save_project(request: Request, job_id: str):
    job = load_job(job_id)
    workers = job["people_data"]
    risk_inputs = job.get("risk_inputs", {})

    temp_dir = UPLOAD_DIR / f"temp_project_{job_id}"
    temp_dir.mkdir(exist_ok=True)

    for worker in workers:
        if hasattr(worker, 'position'):
            position = worker.position
        elif isinstance(worker, dict):
            position = worker.get('position')
        else:
            continue

        if not position:
            continue

        inputs = risk_inputs.get(worker.ID, {})

        if not inputs:
            continue

        template_data = {
            "template_name": position,
            "risks": inputs
        }

        filename = safe_filename(sanitize_filename(position)) + f"{worker.ID}.json"
        file_path = temp_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)

    json_files = list(temp_dir.glob("*.json"))
    if not json_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=404, detail="Нет заполненных работников для сохранения")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in json_files:
            zf.write(file_path, arcname=file_path.name)

    shutil.rmtree(temp_dir, ignore_errors=True)
    org_name = safe_filename(sanitize_filename(job["org_data"].full_name))
    zip_buffer.seek(0)
    try:
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=project_{org_name}.zip"}
        )
    except:
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=project.zip"}
        )


@router.get("/generate/{job_id}")
def generate(request: Request, job_id: str):
    job = load_job(job_id)
    output_dir = UPLOAD_DIR / job_id / "output"
    output_dir.mkdir(exist_ok=True)

    report_template = job.get("rep_template_path")
    if report_template and report_template.exists():
        generate_report(
            report_template_path=report_template,
            output_dir=output_dir,
            org_data=job["org_data"],
            people_data=job["people_data"],
            doc_date=job["doc_date"]
        )
    else:
        print("Шаблон отчёта отсутствует — отчёт не создан")

    zip_path = UPLOAD_DIR / f"{job_id}_cards.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for doc_file in output_dir.glob("Карта*.docx"):
            zipf.write(doc_file, arcname=doc_file.name)

        report_file = output_dir / "Отчет.docx"
        if report_file.exists():
            zipf.write(report_file, arcname="Отчет.docx")

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "workers": job["people_data"],
            "job_id": job_id,
            "generated_count": len(job.get("generated_cards", set())),
            "total_workers": len(job["people_data"]),
            "zip_ready": True
        }
    )


@router.get("/download/{job_id}")
def download_zip(job_id: str, background_tasks: BackgroundTasks):
    zip_path = UPLOAD_DIR / f"{job_id}_cards.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Архив не найден")
    job = load_job(job_id)
    organizationName = job['org_data'].full_name
    background_tasks.add_task(cleanup_job, job_id, zip_path)
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{organizationName}.zip"
    )


def cleanup_job(job_id: str, zip_path: Path):
    if zip_path.exists():
        os.remove(zip_path)
    job_dir = UPLOAD_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


@router.post("/shutdown")
async def shutdown():
    import signal
    import asyncio

    def cleanup_all_temp_files():
        try:
            if UPLOAD_DIR.exists():
                shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
            if UPLOAD_DIR_SEC.exists():
                shutil.rmtree(UPLOAD_DIR_SEC, ignore_errors=True)
        except Exception as e:
            print(f"Ошибка при удалении временных файлов: {e}")

    cleanup_all_temp_files()

    async def stop_server():
        await asyncio.sleep(1)
        print("Остановка сервера...")
        os.kill(os.getpid(), signal.SIGTERM)

    await asyncio.create_task(stop_server())

    return {"status": "shutting down"}

ORG_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "org_templates"

ORG_TEMPLATE_FILES = {
    "people_blank": "people_card_blank.xlsx",
    "people_example": "people_card_example.xlsx",
    "people_pdf": "people_card_example.pdf",
    "org_blank": "organization_card_blank.xlsx",
    "org_example": "organization_card_example.xlsx",
    "org_pdf": "organization_card_example.pdf",
}

@router.get("/org_templates")
def org_templates_page(request: Request):
    return templates.TemplateResponse(
        "org_templates.html",
        {"request": request}
    )


@router.get("/org_templates/download/{file_key}")
def org_templates_download(file_key: str):
    if file_key not in ORG_TEMPLATE_FILES:
        raise HTTPException(status_code=404, detail="Файл не найден")
    file_path = ORG_TEMPLATES_DIR / ORG_TEMPLATE_FILES[file_key]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(file_path, filename=ORG_TEMPLATE_FILES[file_key])


@router.get("/org_templates/view/{file_key}")
def org_templates_view(file_key: str):
    if file_key not in ORG_TEMPLATE_FILES:
        raise HTTPException(status_code=404, detail="Файл не найден")
    file_path = ORG_TEMPLATES_DIR / ORG_TEMPLATE_FILES[file_key]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )


@router.get("/risk_templates")
def risk_templates(request: Request):
    return templates.TemplateResponse(
        "risk_templates.html",
        {"request": request}
    )


DOC_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "doc_templates"

DOC_TEMPLATE_FILES = {
    "card_blank": "card_template.docx",
    "card_example": "card_example.pdf",
    "card_blank_no_jdi": "card_template_no_jdi.docx",
    "card_example_no_jdi": "card_example_no_jdi.pdf",
    "report_blank": "report_template.docx",
    "report_example": "report_example.pdf",
    "report_blank_no_jdi": "report_template_no_jdi.docx",
    "report_example_no_jdi": "report_example_no_jdi.pdf",
}


@router.get("/doc_templates")
def doc_templates_page(request: Request):
    return templates.TemplateResponse(
        "doc_templates.html",
        {"request": request}
    )


@router.get("/doc_templates/download/{file_key}")
def doc_templates_download(file_key: str):
    if file_key not in DOC_TEMPLATE_FILES:
        raise HTTPException(status_code=404, detail="Файл не найден")
    file_path = DOC_TEMPLATES_DIR / DOC_TEMPLATE_FILES[file_key]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(file_path, filename=DOC_TEMPLATE_FILES[file_key])


@router.get("/doc_templates/view/{file_key}")
def doc_templates_view(file_key: str):
    if file_key not in DOC_TEMPLATE_FILES:
        raise HTTPException(status_code=404, detail="Файл не найден")
    file_path = DOC_TEMPLATES_DIR / DOC_TEMPLATE_FILES[file_key]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )

@router.get("/settings/risks")
def risk_settings_page(request: Request, saved: str = ""):
    all_dangers = list(DANGER_DATABASE.values())

    dangers_with_measures = []
    for danger in all_dangers:
        risks_data = []
        for risk in danger.risks:
            measures = get_management_measures(risk.risk_number, risk.management_measures)
            risks_data.append({
                "risk_number": risk.risk_number,
                "risk_name": risk.risk_name,
                "management_measures": measures,
                "measures_text": "\n".join(measures) if measures else ""
            })
        dangers_with_measures.append({
            "danger_number": danger.danger_number,
            "danger_name": danger.danger_name,
            "risks": risks_data
        })

    return templates.TemplateResponse(
        "settings_risks.html",
        {
            "request": request,
            "dangers": dangers_with_measures,
            "saved": saved == "1",
        }
    )


@router.post("/settings/risks")
async def risk_settings_save(request: Request):
    form = await request.form()

    measures_data = {}
    for key, value in form.items():
        if key.startswith("measures_"):
            risk_number = key.replace("measures_", "", 1)
            lines = [line.strip() for line in value.strip().split("\n") if line.strip()]
            measures_data[risk_number] = lines

    save_management_measures(measures_data)

    return RedirectResponse(url="/settings/risks?saved=1", status_code=303)


@router.get("/settings/descriptions")
def settings_descriptions_page(request: Request, saved: str = ""):
    return templates.TemplateResponse(
        "settings_descriptions.html",
        {
            "request": request,
            "degree_info": get_degree_info(),
            "chance_info": get_chance_info(),
            "coeff_info": get_coeff_info(),
            "control_info": get_control_info(),
            "saved": saved == "1",
        }
    )


@router.post("/settings/descriptions")
async def settings_descriptions_save(request: Request):
    form = await request.form()

    degree_info = {}
    chance_info = {}
    coeff_info = {}
    control_keys = {}
    control_values = {}

    for key, value in form.items():
        if key.startswith("degree_"):
            idx = key.replace("degree_", "", 1)
            degree_info[idx] = value.strip()
        elif key.startswith("chance_"):
            idx = key.replace("chance_", "", 1)
            chance_info[idx] = value.strip()
        elif key.startswith("coeff_"):
            idx = key.replace("coeff_", "", 1)
            coeff_info[idx] = value.strip()
        elif key.startswith("control_key_"):
            idx = key.replace("control_key_", "", 1)
            control_keys[idx] = value
        elif key.startswith("control_value_"):
            idx = key.replace("control_value_", "", 1)
            control_values[idx] = value.strip()

    control_info = {}
    for idx, level in control_keys.items():
        control_info[level] = control_values.get(idx, "")

    data_to_save = {}
    if degree_info:
        data_to_save["DEGREE_INFO"] = degree_info
    if chance_info:
        data_to_save["CHANCE_INFO"] = chance_info
    if coeff_info:
        data_to_save["COEFF_INFO"] = coeff_info
    if control_info:
        data_to_save["CONTROL_INFO"] = control_info

    if data_to_save:
        save_descriptions(data_to_save)

    return RedirectResponse(url="/settings/descriptions?saved=1", status_code=303)


@router.get("/settings/ranges")
def settings_ranges_page(request: Request, saved: str = "", error: str = ""):
    return templates.TemplateResponse(
        "settings_ranges.html",
        {
            "request": request,
            "summary_info": get_summary_info_dict(),
            "summary_info_aplication": get_summary_info_aplication_dict(),
            "saved": saved == "1",
            "error": error,
        }
    )


@router.post("/settings/ranges")
async def settings_ranges_save(request: Request):
    form = await request.form()

    summary_thresholds = {}
    summary_levels = {}
    aplication_thresholds = {}
    aplication_levels = {}

    for key, value in form.items():
        if key.startswith("summary_threshold_"):
            idx = key.replace("summary_threshold_", "", 1)
            summary_thresholds[idx] = value.strip()
        elif key.startswith("summary_level_"):
            idx = key.replace("summary_level_", "", 1)
            summary_levels[idx] = value
        elif key.startswith("aplication_threshold_"):
            idx = key.replace("aplication_threshold_", "", 1)
            aplication_thresholds[idx] = value.strip()
        elif key.startswith("aplication_level_"):
            idx = key.replace("aplication_level_", "", 1)
            aplication_levels[idx] = value

    try:
        summary_info = {}
        for idx, threshold_str in summary_thresholds.items():
            threshold = float(threshold_str.replace(",", "."))
            level = summary_levels.get(idx, "")
            summary_info[str(threshold)] = level

        aplication_info = {}
        for idx, threshold_str in aplication_thresholds.items():
            threshold = float(threshold_str.replace(",", "."))
            level = aplication_levels.get(idx, "")
            aplication_info[str(threshold)] = level
    except ValueError:
        return RedirectResponse(
            url="/settings/ranges?error=invalid_number",
            status_code=303
        )

    summary_keys = sorted([float(k) for k in summary_info.keys()])
    for i in range(len(summary_keys) - 1):
        if summary_keys[i] >= summary_keys[i + 1]:
            return RedirectResponse(
                url="/settings/ranges?error=order",
                status_code=303
            )

    aplication_keys = sorted([float(k) for k in aplication_info.keys()])
    for i in range(len(aplication_keys) - 1):
        if aplication_keys[i] >= aplication_keys[i + 1]:
            return RedirectResponse(
                url="/settings/ranges?error=order",
                status_code=303
            )

    save_ranges({
        "SUMMARY_INFO": summary_info,
        "SUMMARY_INFO_APLICATION": aplication_info,
    })

    return RedirectResponse(url="/settings/ranges?saved=1", status_code=303)


@router.post("/settings/reset-descriptions")
async def settings_reset_descriptions(request: Request):
    reset_descriptions()
    return RedirectResponse(url="/settings/descriptions", status_code=303)


@router.post("/settings/reset-ranges")
async def settings_reset_ranges(request: Request):
    reset_ranges()
    return RedirectResponse(url="/settings/ranges", status_code=303)


@router.post("/settings/reset-risks")
async def settings_reset_risks(request: Request):
    reset_risks()
    return RedirectResponse(url="/settings/risks", status_code=303)