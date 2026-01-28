from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import uuid
import os
import zipfile
from typing import List

from generate_cards import *
from getWorkerRisks import get_org_dangers, get_worker_risks
from RisksAndDangers import DANGER_DATABASE, DEGREE_INFO, CHANCE_INFO, COEFF_INFO
from storage import save_job, load_job

router = APIRouter()

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("temp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/")
def upload_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


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

    return templates.TemplateResponse(
        "select_dangers.html",
        {
            "request": request,
            "dangers": list(DANGER_DATABASE.values()),
            "job_id": job_id
        }
    )


@router.post("/select-dangers")
async def select_dangers(
    request: Request,
    job_id: str = Form(...),
    danger_ids: List[int] = Form(default=[])
):
    job = load_job(job_id)
    job["selected_danger_ids"] = danger_ids
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
    existing_inputs = job["risk_inputs"].get(worker.position, {})

    return templates.TemplateResponse(
        "worker_risks.html",
        {
            "request": request,
            "job_id": job_id,
            "worker_idx": worker_idx,
            "worker": worker,
            "dangers": org_dangers,
            "existing": existing_inputs,
            "degree_info": DEGREE_INFO,
            "chance_info": CHANCE_INFO,
            "coeff_info": COEFF_INFO
        }
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
        return RedirectResponse(url=f"/generate/{job_id}", status_code=303)


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

    
    zip_path = UPLOAD_DIR / f"{job_id}_cards.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        for doc_file in output_dir.glob("Карта*.docx"):
            zipf.write(doc_file, arcname=doc_file.name)

        
        report_file = output_dir / "отчет.docx"
        if report_file.exists():
            zipf.write(report_file, arcname="отчет.docx")

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
    """Очистка временных файлов и остановка сервера"""
    import signal
    import asyncio

    def cleanup_all_temp_files():
        """Удаляет все временные файлы"""
        try:
            if UPLOAD_DIR.exists():
                shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
                print("Временные файлы удалены")
        except Exception as e:
            print(f"Ошибка при удалении временных файлов: {e}")

    
    cleanup_all_temp_files()

    async def stop_server():
        await asyncio.sleep(1)
        print("Остановка сервера...")
        os.kill(os.getpid(), signal.SIGTERM)

    await asyncio.create_task(stop_server())

    return {"status": "shutting down"}
