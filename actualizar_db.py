from app import app, db

def actualizar_base_datos():
    with app.app_context():
        print("Eliminando tablas existentes...")
        db.drop_all()
        print("Creando nuevas tablas...")
        db.create_all()
        print("Base de datos actualizada correctamente!")

if __name__ == '__main__':
    actualizar_base_datos()