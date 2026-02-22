from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
import json
import shutil
import uuid
import os
import zipfile
from datetime import date
from generate_cards import *
from getWorkerRisks import get_org_dangers, get_worker_risks
from RisksAndDangers import DANGER_DATABASE, DEGREE_INFO, CHANCE_INFO, COEFF_INFO
from storage import save_job, load_job
from parser import translit
import re
import io
from pathlib import Path

router = APIRouter()

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("temp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
            "degree_info": DEGREE_INFO,
            "chance_info": CHANCE_INFO,
            "coeff_info": COEFF_INFO,
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

    save_job(
        job_id=job_id,
        card_template_path=card_template_path,
        rep_template_path=rep_template_path,
        people_path=people_path,
        org_path=org_path,
        doc_date=doc_date,
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
        for w in workers:
            pos = w.position if hasattr(w, 'position') else w.get('position')
            if pos == position:
                return w
        return None

    for json_file in extract_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                template_data = json.load(f)

            position = template_data.get("template_name")
            if not position:
                position = json_file.stem

            worker = find_worker(position)

            if not worker:
                print(f"Предупреждение: работник с должностью '{position}' не найден. Пропускаем.")
                continue

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

            job["generated_cards"].add(position)

        except Exception as e:
            print(f"Ошибка при обработке файла {json_file}: {e}")
            continue

    shutil.rmtree(extract_dir, ignore_errors=True)
    if zip_path.exists():
        zip_path.unlink()
    from storage import save_job_data
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
    return templates.TemplateResponse(
        "select_worker_risks.html",
        {
            "request": request,
            "workers": job["people_data"],
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

    save_job(
        job_id=job_id,
        card_template_path=card_template_path,
        rep_template_path=rep_template_path,
        people_path=people_path,
        org_path=org_path,
        doc_date=doc_date,
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
    saved_inputs = job["risk_inputs"].get(worker.position, {})

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
            "degree_info": DEGREE_INFO,
            "chance_info": CHANCE_INFO,
            "coeff_info": COEFF_INFO
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
        "template_name": translit(worker.position),
        "risks": inputs
    }

    json_str = json.dumps(template_data, ensure_ascii=False, indent=2)
    filename = f"{translit(worker.position)}_template.json".replace(" ", "_")

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
            r_id = r_str  # уже с точками
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

    job["risk_inputs"][worker.position] = inputs

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

    job["generated_cards"].add(worker.position)

    print(f"Сгенерирована карта для: {worker.position}")

    next_idx = worker_idx + 1
    if next_idx < len(workers):
        return RedirectResponse(url=f"/worker_risks/{job_id}/{next_idx}", status_code=303)
    else:
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

    job["risk_inputs"][worker.position] = inputs

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

    job["generated_cards"].add(worker.position)
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

        inputs = risk_inputs.get(position, {})
        if not inputs:
            continue

        template_data = {
            "template_name": position,
            "risks": inputs
        }

        filename = sanitize_filename(position) + ".json"
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
    org_name = sanitize_filename(job["org_data"].full_name)
    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=project_{org_name}.zip"}
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
            dangers=job["org_dangers"],
            people_data=job["people_data"],
            doc_date=job["doc_date"]
        )
    else:
        print("Шаблон отчёта отсутствует — отчёт не создан")

    # Always create/recreate the ZIP file
    zip_path = UPLOAD_DIR / f"{job_id}_cards.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Все карты
        for doc_file in output_dir.glob("Карта*.docx"):
            zipf.write(doc_file, arcname=doc_file.name)

        # Отчёт
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
                print("Временные файлы удалены")
        except Exception as e:
            print(f"Ошибка при удалении временных файлов: {e}")

    # Запускаем очистку
    cleanup_all_temp_files()

    # Останавливаем сервер через 1 секунду
    async def stop_server():
        await asyncio.sleep(1)
        print("Остановка сервера...")
        os.kill(os.getpid(), signal.SIGTERM)

    await asyncio.create_task(stop_server())

    return {"status": "shutting down"}