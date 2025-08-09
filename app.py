from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import qrcode
from io import BytesIO
import base64
import secrets
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qr_tokens.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SERVER_URL = 'http://tu_ia_aqui:5000/'
db = SQLAlchemy(app)

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), nullable=False)
    usado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_uso = db.Column(db.DateTime, nullable=True)

with app.app_context():
    db.create_all()

def generar_qr(token, url_base):
    """Genera un código QR con el token y la URL base"""
    url = f"{url_base}/validar/{token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir la imagen a base64 para mostrarla en HTML
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar_qr', methods=['POST'])
def generar():
    try:
        data = request.form
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        dni = data.get('dni')
        
        if not all([nombre, apellido, dni]):
            return jsonify({'error': 'Todos los campos son requeridos'}), 400
        
        # Generar token único
        token = secrets.token_urlsafe(32)
        
        # Guardar en la base de datos
        nuevo_token = Token(
            token=token,
            nombre=nombre,
            apellido=apellido,
            dni=dni
        )
        db.session.add(nuevo_token)
        db.session.commit()
        
        # ⚠️ IP FIJA PARA EL QR
        url_base = SERVER_URL.rstrip('/')
        qr_base64 = generar_qr(token, url_base)
        qr_url = f"{url_base}/validar/{token}"
        
        return render_template('qr.html', 
                      qr_image=qr_base64, 
                      nombre=nombre, 
                      apellido=apellido, 
                      dni=dni,
                      qr_url=qr_url)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/validar/<token>')
def validar(token):
    token_db = Token.query.filter_by(token=token).first()
    
    if not token_db:
        return render_template('error.html', mensaje='Token no válido')
    
    if token_db.usado:
        return render_template('error.html', mensaje='Este QR ya ha sido utilizado')
    
    # Marcar como usado
    token_db.usado = True
    token_db.fecha_uso = datetime.utcnow()
    db.session.commit()
    
    return render_template('validacion.html', 
                         nombre=token_db.nombre,
                         apellido=token_db.apellido,
                         dni=token_db.dni)

@app.route('/admin')
def admin():
    tokens = Token.query.order_by(Token.fecha_creacion.desc()).all()
    return render_template('admin.html', tokens=tokens)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
