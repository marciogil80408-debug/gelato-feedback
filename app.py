import os
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração do Banco de Dados PostgreSQL (Render) ou SQLite local de segurança
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///gelato.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Tabela de Representantes Cadastrados Permanentemente
class RepresentanteModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)

# Tabela de Clientes/Lojas Cadastrados Permanentemente
class ClienteModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    whatsapp = db.Column(db.String(50), nullable=True)
    representante = db.Column(db.String(100), nullable=True)

# Tabela de Feedbacks / Avaliações dos Clientes
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_registro = db.Column(db.DateTime, nullable=False)
    representante = db.Column(db.String(100), nullable=False)
    cliente = db.Column(db.String(100), nullable=False)
    nota_representante = db.Column(db.Integer, nullable=True)
    visitas_suporte = db.Column(db.String(150), nullable=True)
    obs_visitas = db.Column(db.Text, nullable=True)
    falta_produto = db.Column(db.String(150), nullable=True)
    qual_falta = db.Column(db.Text, nullable=True)
    entrega_status = db.Column(db.String(150), nullable=True)
    obs_entrega = db.Column(db.Text, nullable=True)
    nota_geral = db.Column(db.Integer, nullable=True)
    obs_geral = db.Column(db.Text, nullable=True)
    comentario = db.Column(db.Text, nullable=True)

with app.app_context():
    # SEGURO: Apenas cria tabelas novas se não existirem, NUNCA apaga dados existentes!
    db.create_all()

# Página de Avaliação do Cliente
@app.route('/')
def avaliacao():
    representante = request.args.get('rep', 'Representante')
    cliente = request.args.get('cliente', 'Cliente')
    return render_template('avaliacao.html', representante=representante, cliente=cliente)

# Rota para Cadastrar Representante
@app.route('/api/cadastrar_representante', methods=['POST'])
def cadastrar_representante():
    dados = request.json
    nome = dados.get('nome', '').strip()
    if not nome:
        return jsonify({'status': 'erro', 'mensagem': 'Nome obrigatório'}), 400
    try:
        existe = RepresentanteModel.query.filter_by(nome=nome).first()
        if not existe:
            db.session.add(RepresentanteModel(nome=nome))
            db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Rota para Cadastrar Cliente
@app.route('/api/cadastrar_cliente', methods=['POST'])
def cadastrar_cliente():
    dados = request.json
    nome = dados.get('nome', '').strip()
    whatsapp = dados.get('whatsapp', '').strip()
    representante = dados.get('representante', '').strip()
    if not nome:
        return jsonify({'status': 'erro', 'mensagem': 'Nome do cliente obrigatório'}), 400
    try:
        db.session.add(ClienteModel(nome=nome, whatsapp=whatsapp, representante=representante))
        db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Rota para buscar dados salvos no disparador
@app.route('/api/dados_cadastrados')
def dados_cadastrados():
    reps = [r.nome for r in RepresentanteModel.query.all()]
    clientes = [{'id': c.id, 'nome': c.nome, 'whatsapp': c.whatsapp, 'representante': c.representante} for c in ClienteModel.query.all()]
    return jsonify({'representantes': reps, 'clientes': clientes})

# Rota para Salvar o Feedback preenchido pelo cliente
@app.route('/salvar', methods=['POST'])
def salvar():
    dados = request.json
    try:
        fuso_br = pytz.timezone('America/Sao_Paulo')
        agora_brasil = datetime.now(fuso_br)

        novo = Feedback(
            data_registro=agora_brasil,
            representante=dados.get('representante'),
            cliente=dados.get('cliente'),
            nota_representante=int(dados.get('nota_representante', 0)),
            visitas_suporte=dados.get('visitas_suporte'),
            obs_visitas=dados.get('obs_visitas', ''),
            falta_produto=dados.get('falta_produto'),
            qual_falta=dados.get('qual_falta', ''),
            entrega_status=dados.get('entrega_status'),
            obs_entrega=dados.get('obs_entrega', ''),
            nota_geral=int(dados.get('nota_geral', 0)),
            obs_geral=dados.get('obs_geral', ''),
            comentario=dados.get('comentario', '')
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print("Erro ao salvar:", str(e))
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Painel de Gestão e Resultados (Com dados para os gráficos)
@app.route('/painel')
def painel():
    feedbacks = Feedback.query.order_by(Feedback.id.desc()).all()
    clientes = ClienteModel.query.all()
    representantes = RepresentanteModel.query.all()
    return render_template('painel.html', feedbacks=feedbacks, clientes=clientes, representantes=representantes)

# Tela do Disparador WhatsApp e Cadastros
@app.route('/disparar')
def disparar():
    return render_template('disparar.html')

if __name__ == '__main__':
    app.run(debug=True)