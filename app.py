import os
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, session
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa

app = Flask(__name__)

# CHAVE SECRETA E SENHA DE ADMINISTRADOR
app.secret_key = 'gelato_fran_secret_key_segura'
SENHA_ADMIN = "1234"

# Configuração do Banco de Dados PostgreSQL (Render) ou SQLite local de segurança
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///gelato.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Tabela de Representantes Cadastrados Permanentemente
class RepresentanteModel(db.Model):
    __tablename__ = 'representante_model'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)

# Tabela de Rotas Cadastradas (Ex: Rota de Natal, Rota de Sousa, Rota de Fortaleza)
class RotaModel(db.Model):
    __tablename__ = 'rota_model'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)

# Tabela de Clientes/Lojas (Com Rota, Cidade e Estado)
class ClienteModel(db.Model):
    __tablename__ = 'cliente_model'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    whatsapp = db.Column(db.String(50), nullable=True)
    representante = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(10), nullable=True)
    rota = db.Column(db.String(100), nullable=True)

# Tabela de Feedbacks / Avaliações dos Clientes
class Feedback(db.Model):
    __tablename__ = 'feedback'
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
    db.create_all()
    
    # SEGURANÇA AUTOMÁTICA: Adiciona colunas ausentes sem NUNCA apagar dados existentes
    try:
        inspector = sa.inspect(db.engine)
        tables = inspector.get_table_names()
        
        with db.engine.connect() as conn:
            if 'feedback' in tables:
                col_fb = [c['name'] for c in inspector.get_columns('feedback')]
                colunas_fb = [
                    ('obs_visitas', 'TEXT'), ('qual_falta', 'TEXT'),
                    ('obs_entrega', 'TEXT'), ('obs_geral', 'TEXT'),
                    ('comentario', 'TEXT'), ('nota_representante', 'INTEGER'),
                    ('visitas_suporte', 'VARCHAR(150)'), ('falta_produto', 'VARCHAR(150)'),
                    ('entrega_status', 'VARCHAR(150)'), ('nota_geral', 'INTEGER')
                ]
                for col_nome, col_tipo in colunas_fb:
                    if col_nome not in col_fb:
                        conn.execute(sa.text(f'ALTER TABLE feedback ADD COLUMN {col_nome} {col_tipo}'))
                        conn.commit()

            if 'cliente_model' in tables:
                col_cl = [c['name'] for c in inspector.get_columns('cliente_model')]
                if 'cidade' not in col_cl:
                    conn.execute(sa.text('ALTER TABLE cliente_model ADD COLUMN cidade VARCHAR(100)'))
                    conn.commit()
                if 'estado' not in col_cl:
                    conn.execute(sa.text('ALTER TABLE cliente_model ADD COLUMN estado VARCHAR(10)'))
                    conn.commit()
                if 'rota' not in col_cl:
                    conn.execute(sa.text('ALTER TABLE cliente_model ADD COLUMN rota VARCHAR(100)'))
                    conn.commit()
    except Exception as e:
        print("Aviso na checagem de colunas:", str(e))

# Página de Avaliação do Cliente
@app.route('/')
def avaliacao():
    representante = request.args.get('rep', 'Representante')
    cliente = request.args.get('cliente', 'Cliente')
    return render_template('avaliacao.html', representante=representante, cliente=cliente)

# Cadastrar Representante
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

# Cadastrar Nova Rota (Ex: Rota de Sousa, Rota de Natal)
@app.route('/api/cadastrar_rota', methods=['POST'])
def cadastrar_rota():
    dados = request.json
    nome = dados.get('nome', '').strip()
    if not nome:
        return jsonify({'status': 'erro', 'mensagem': 'Nome da rota obrigatório'}), 400
    try:
        existe = RotaModel.query.filter_by(nome=nome).first()
        if not existe:
            db.session.add(RotaModel(nome=nome))
            db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Cadastrar Cliente com Rota
@app.route('/api/cadastrar_cliente', methods=['POST'])
def cadastrar_cliente():
    dados = request.json
    nome = dados.get('nome', '').strip()
    whatsapp = dados.get('whatsapp', '').strip()
    representante = dados.get('representante', '').strip()
    cidade = dados.get('cidade', '').strip()
    estado = dados.get('estado', '').strip()
    rota = dados.get('rota', '').strip()
    
    if not nome:
        return jsonify({'status': 'erro', 'mensagem': 'Nome do cliente obrigatório'}), 400
    try:
        novo = ClienteModel(
            nome=nome, 
            whatsapp=whatsapp, 
            representante=representante,
            cidade=cidade,
            estado=estado,
            rota=rota
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Verificar Senha do Administrador
@app.route('/api/verificar_senha', methods=['POST'])
def verificar_senha():
    dados = request.json
    senha = dados.get('senha', '')
    if senha == SENHA_ADMIN:
        session['admin_autorizado'] = True
        return jsonify({'status': 'sucesso'})
    return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'}), 403

# Editar Cliente (Permitindo trocar a rota facilmente)
@app.route('/api/editar_cliente', methods=['POST'])
def editar_cliente():
    if not session.get('admin_autorizado'):
        return jsonify({'status': 'erro', 'mensagem': 'Sessão expirada. Faça login novamente.'}), 403
    
    dados = request.json
    cliente_id = dados.get('id')
    cliente = ClienteModel.query.get(cliente_id)
    if not cliente:
        return jsonify({'status': 'erro', 'mensagem': 'Cliente não encontrado'}), 404
    
    try:
        cliente.nome = dados.get('nome', cliente.nome).strip()
        cliente.whatsapp = dados.get('whatsapp', cliente.whatsapp).strip()
        cliente.representante = dados.get('representante', cliente.representante).strip()
        cliente.cidade = dados.get('cidade', cliente.cidade).strip()
        cliente.estado = dados.get('estado', cliente.estado).strip()
        cliente.rota = dados.get('rota', cliente.rota).strip()
        
        db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Zerar Feedbacks de Teste (Protegido por Senha)
@app.route('/api/zerar_feedbacks', methods=['POST'])
def zerar_feedbacks():
    dados = request.json
    senha = dados.get('senha', '')
    if senha != SENHA_ADMIN:
        return jsonify({'status': 'erro', 'mensagem': 'Senha de administrador incorreta!'}), 403
    
    try:
        Feedback.query.delete()
        db.session.commit()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# Retornar Dados Cadastrados (Clientes, Representantes e Rotas)
@app.route('/api/dados_cadastrados')
def dados_cadastrados():
    reps = [r.nome for r in RepresentanteModel.query.order_by(RepresentanteModel.nome).all()]
    rotas = [r.nome for r in RotaModel.query.order_by(RotaModel.nome).all()]
    clientes = [{
        'id': c.id, 
        'nome': c.nome, 
        'whatsapp': c.whatsapp, 
        'representante': c.representante,
        'cidade': c.cidade or 'Não informada',
        'estado': c.estado or 'RN',
        'rota': c.rota or 'Geral'
    } for c in ClienteModel.query.all()]
    return jsonify({'representantes': reps, 'rotas': rotas, 'clientes': clientes})

# Salvar Feedback
@app.route('/salvar', methods=['POST'])
def salvar():
    dados = request.json
    try:
        fuso_br = pytz.timezone('America/Sao_Paulo')
        agora_brasil = datetime.now(fuso_br).replace(tzinfo=None)

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

# Exportar CSV para Excel
def escape_csv(val):
    val_str = str(val or '')
    val_str = val_str.replace('"', '""').replace('\n', ' ')
    return f'"{val_str}"'

@app.route('/exportar_csv')
def exportar_csv():
    try:
        feedbacks = Feedback.query.order_by(Feedback.id.desc()).all()
        
        def generate():
            yield 'ID;Data/Hora;Cliente/Loja;Representante;Nota Rep.;Suporte/Visitas;Obs Visitas;Falta Produto;Qual Falta;Status Entrega;Obs Entrega;Nota Geral;Obs Geral;Comentario\n'
            for f in feedbacks:
                linha = [
                    str(f.id),
                    f.data_registro.strftime('%d/%m/%Y %H:%M') if f.data_registro else '',
                    f.cliente or '',
                    f.representante or '',
                    str(f.nota_representante or ''),
                    f.visitas_suporte or '',
                    f.obs_visitas or '',
                    f.falta_produto or '',
                    f.qual_falta or '',
                    f.entrega_status or '',
                    f.obs_entrega or '',
                    str(f.nota_geral or ''),
                    f.obs_geral or '',
                    f.comentario or ''
                ]
                yield ';'.join([escape_csv(val) for val in linha]) + '\n'

        return Response(generate(), mimetype='text/csv; charset=utf-8', headers={"Content-Disposition": "attachment; filename=relatorio_gelato_da_fran.csv"})
    except Exception as e:
        return str(e), 500

# Painel
@app.route('/painel')
def painel():
    try:
        feedbacks = Feedback.query.order_by(Feedback.id.desc()).all()
        representantes = RepresentanteModel.query.all()
    except Exception as e:
        print("Erro ao carregar painel:", str(e))
        feedbacks, representantes = [], []
    return render_template('painel.html', feedbacks=feedbacks, representantes=representantes)

# Tela de Clientes
@app.route('/clientes')
def clientes():
    if not session.get('admin_autorizado'):
        return redirect(url_for('painel'))
    try:
        lista_clientes = ClienteModel.query.order_by(ClienteModel.nome).all()
        rotas = [r.nome for r in RotaModel.query.order_by(RotaModel.nome).all()]
    except Exception as e:
        print("Erro ao carregar clientes:", str(e))
        lista_clientes, rotas = [], []
    return render_template('clientes.html', clientes=lista_clientes, rotas=rotas)

# Tela do Disparador
@app.route('/disparar')
def disparar():
    return render_template('disparar.html')

if __name__ == '__main__':
    app.run(debug=True)