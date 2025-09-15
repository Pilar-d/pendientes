from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from models import db, Usuario, Tarea
from sqlalchemy.exc import OperationalError
from sqlalchemy import text  # Importar la función text
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui-muy-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tareas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Crear tablas de base de datos (solo si no existen)
with app.app_context():
    try:
        # Verificar si la tabla ya existe y tiene las columnas necesarias
        # USAR text() para declarar explícitamente la expresión SQL
        db.session.execute(text("SELECT fecha_limite, categoria FROM tarea LIMIT 1")).fetchall()
        print("La base de datos ya tiene las columnas necesarias")
    except OperationalError:
        print("La base de datos necesita actualización. Creando tablas...")
        db.drop_all()
        db.create_all()
        print("Tablas creadas correctamente")

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and usuario.check_password(password):
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if Usuario.query.filter_by(username=username).first():
            flash('El usuario ya existe', 'error')
            return redirect(url_for('register'))
        
        nuevo_usuario = Usuario(username=username)
        nuevo_usuario.set_password(password)
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

# Rutas de tareas
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Obtener parámetros de búsqueda y ordenamiento
    q = request.args.get('q', '')
    orden = request.args.get('orden', 'recientes')
    
    # Consulta base con manejo de errores
    try:
        consulta = Tarea.query.filter_by(usuario_id=session['user_id'])
        
        # Aplicar búsqueda
        if q:
            consulta = consulta.filter(
                (Tarea.titulo.ilike(f'%{q}%')) | (Tarea.descripcion.ilike(f'%{q}%'))
            )
        
        # Aplicar ordenamiento
        if orden == 'recientes':
            consulta = consulta.order_by(Tarea.creada_en.desc())
        elif orden == 'antiguas':
            consulta = consulta.order_by(Tarea.creada_en.asc())
        elif orden == 'titulo':
            consulta = consulta.order_by(Tarea.titulo.asc())
        
        tareas = consulta.all()
        
    except OperationalError as e:
        # Si hay error, probablemente falten columnas en la base de datos
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        tareas = []
        # Intentar recrear la base de datos
        try:
            with app.app_context():
                db.drop_all()
                db.create_all()
                flash('Base de datos reinicializada. Por favor, regístrate nuevamente.', 'info')
        except Exception as e:
            flash(f'Error crítico: {str(e)}', 'error')
    
    # Pasar la fecha actual para comparaciones
    hoy = datetime.now().date()
    
    return render_template('index.html', 
                         tareas=tareas, 
                         username=session['username'],
                         q=q,
                         orden=orden,
                         hoy=hoy)

@app.route('/crear', methods=['POST'])
def crear():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    
    try:
        titulo = request.form['titulo']
        descripcion = request.form.get('descripcion', '')
        fecha_limite_str = request.form['fecha_limite']
        categoria = request.form['categoria']
        
        # Convertir la fecha de string a objeto date
        fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
        
        nueva_tarea = Tarea(
            titulo=titulo,
            descripcion=descripcion,
            fecha_limite=fecha_limite,
            categoria=categoria,
            usuario_id=session['user_id']
        )
        
        db.session.add(nueva_tarea)
        db.session.commit()
        
        flash('Tarea creada exitosamente', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        # Si el error es por columnas faltantes, recrear la base de datos
        if "no such column" in str(e):
            try:
                with app.app_context():
                    db.drop_all()
                    db.create_all()
                    flash('Base de datos actualizada. Por favor, crea la tarea nuevamente.', 'info')
            except Exception as db_error:
                flash(f'Error crítico al actualizar la base de datos: {str(db_error)}', 'error')
        else:
            flash(f'Error al crear la tarea: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/editar/<int:tarea_id>', methods=['GET', 'POST'])
def editar(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        
        # Verificar que la tarea pertenece al usuario actual
        if tarea.usuario_id != session['user_id']:
            flash('No tienes permisos para editar esta tarea', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            tarea.titulo = request.form['titulo']
            tarea.descripcion = request.form.get('descripcion', '')
            
            # Actualizar fecha límite
            fecha_limite_str = request.form.get('fecha_limite', '')
            if fecha_limite_str:
                tarea.fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
            else:
                tarea.fecha_limite = None
            
            # Actualizar categoría
            tarea.categoria = request.form.get('categoria', 'laboral')
            
            db.session.commit()
            flash('Tarea actualizada exitosamente', 'success')
            return redirect(url_for('index'))
        
        return render_template('editar.html', tarea=tarea)
    
    except OperationalError as e:
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('index'))

@app.route('/toggle/<int:tarea_id>', methods=['POST'])
def toggle(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        
        # Verificar que la tarea pertenece al usuario actual
        if tarea.usuario_id != session['user_id']:
            flash('No tienes permisos para modificar esta tarea', 'error')
            return redirect(url_for('index'))
        
        tarea.completada = not tarea.completada
        db.session.commit()
        
        return redirect(url_for('index'))
    
    except OperationalError as e:
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('index'))

@app.route('/eliminar/<int:tarea_id>', methods=['POST'])
def eliminar(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        
        # Verificar que la tarea pertenece al usuario actual
        if tarea.usuario_id != session['user_id']:
            flash('No tienes permisos para eliminar esta tarea', 'error')
            return redirect(url_for('index'))
        
        db.session.delete(tarea)
        db.session.commit()
        flash('Tarea eliminada exitosamente', 'success')
        
        return redirect(url_for('index'))
    
    except OperationalError as e:
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('index'))

# Ruta para forzar la actualización de la base de datos
@app.route('/actualizar-db')
def actualizar_db():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            flash('Base de datos actualizada correctamente. Por favor, regístrate nuevamente.', 'success')
            session.clear()
        return redirect(url_for('register'))
    except Exception as e:
        flash(f'Error al actualizar la base de datos: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)