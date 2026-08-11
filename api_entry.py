from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from routes import pages

app = FastAPI()
app.include_router(pages.router)
templates = Jinja2Templates(directory="templates")