from app import app, db
from models import Usuario, Tarea

with app.app_context():
    # Crear todas las tablas
    db.create_all()
    print("✅ Tablas creadas exitosamente!")
    print("📊 Tablas creadas: usuario, tarea")