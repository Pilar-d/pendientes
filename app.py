from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecreto"

# Configuración SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tareas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================
# MODELOS
# =====================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tareas = db.relationship('Tarea', backref='usuario', lazy=True)

class Tarea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    completada = db.Column(db.Boolean, default=False)
    creada_en = db.Column(db.DateTime, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

# =====================
# RUTAS DE AUTENTICACIÓN
# =====================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if Usuario.query.filter_by(username=username).first():
            flash('El usuario ya existe', 'danger')
        elif not username or not password:
            flash('Completa todos los campos', 'warning')
        else:
            nuevo_usuario = Usuario(
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Usuario registrado con éxito', 'success')
            return redirect(url_for('login'))

    return render_template('registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        usuario = Usuario.query.filter_by(username=username).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            session['username'] = usuario.username
            session['user_id'] = usuario.id
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))

# =====================
# RUTAS DE TAREAS
# =====================
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['user_id'])
    if not usuario:
        session.pop('user_id', None)
        session.pop('username', None)
        flash('Usuario no encontrado. Inicia sesión nuevamente.', 'warning')
        return redirect(url_for('login'))

    tareas_usuario = usuario.tareas
    q = request.args.get('q', '')
    orden = request.args.get('orden', 'recientes')

    # Filtrar tareas
    if q:
        tareas_filtradas = [t for t in tareas_usuario if q.lower() in t.titulo.lower()]
    else:
        tareas_filtradas = list(tareas_usuario)

    # Ordenar tareas
    if orden == 'recientes':
        tareas_filtradas.sort(key=lambda t: t.creada_en, reverse=True)
    elif orden == 'antiguas':
        tareas_filtradas.sort(key=lambda t: t.creada_en)
    elif orden == 'titulo':
        tareas_filtradas.sort(key=lambda t: t.titulo.lower())

    return render_template('index.html', tareas=tareas_filtradas, q=q, orden=orden, username=session['username'])


@app.route('/crear', methods=['POST'])
def crear():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    titulo = request.form['titulo'].strip()
    descripcion = request.form.get('descripcion', '').strip()
    if titulo:
        nueva_tarea = Tarea(
            titulo=titulo,
            descripcion=descripcion,
            usuario_id=session['user_id']
        )
        db.session.add(nueva_tarea)
        db.session.commit()

    return redirect(url_for('index'))


@app.route('/toggle/<int:tarea_id>', methods=['POST'])
def toggle(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tarea = Tarea.query.get_or_404(tarea_id)
    if tarea.usuario_id != session['user_id']:
        flash('No puedes modificar esta tarea', 'danger')
        return redirect(url_for('index'))

    tarea.completada = not tarea.completada
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/eliminar/<int:tarea_id>', methods=['POST'])
def eliminar(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tarea = Tarea.query.get_or_404(tarea_id)
    if tarea.usuario_id != session['user_id']:
        flash('No puedes eliminar esta tarea', 'danger')
        return redirect(url_for('index'))

    db.session.delete(tarea)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/editar/<int:tarea_id>', methods=['GET', 'POST'])
def editar(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tarea = Tarea.query.get_or_404(tarea_id)
    if tarea.usuario_id != session['user_id']:
        flash('No puedes editar esta tarea', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        tarea.titulo = request.form.get('titulo', tarea.titulo).strip()
        tarea.descripcion = request.form.get('descripcion', tarea.descripcion).strip()
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('editar.html', tarea=tarea)

# =====================
# EJECUCIÓN
# =====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea la base de datos y tablas si no existen
    app.run(debug=True)
