
from flask import Flask
from database import db
import os

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.secret_key = "krs-ai-secret-key"

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///KRSAi.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Import model
from app import models

# Membuat tabel database jika belum tersedia
with app.app_context():
    db.create_all()

# Import route aplikasi
from app import main
from app.admin import admin_bp

app.register_blueprint(admin_bp)
