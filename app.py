from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'lava_rapido_secret_key_autolub'

# Configuração de Banco de Dados (Compatível com SQLite local e PostgreSQL/Supabase na Nuvem)
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect("LavaRapidoAutoLub.db", timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if DATABASE_URL:
        cursor.execute("CREATE TABLE IF NOT EXISTS Usuarios (ID SERIAL PRIMARY KEY, Nome TEXT UNIQUE, Senha TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Clientes (ID SERIAL PRIMARY KEY, Nome TEXT, Endereco TEXT, Telefone TEXT, ModeloMoto TEXT, AnoMoto TEXT, KM TEXT, Placa TEXT, KMEntrada TEXT, KMSaida TEXT, DataEntrada TEXT, DataSaida TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Vendas (ID SERIAL PRIMARY KEY, ClienteID INTEGER, Servico TEXT, ValorTotal REAL, ValorPago REAL, DataCompra TEXT, FormaPagamento TEXT, Observacao TEXT, CustoInsumos TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Produtos (ID TEXT PRIMARY KEY, NomeProduto TEXT, Descricao TEXT, Preco REAL, QtdEstoque REAL DEFAULT 0.0, UnidadeMedida TEXT DEFAULT 'un', CustoCompra REAL DEFAULT 0.0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Despesas (ID SERIAL PRIMARY KEY, Descricao TEXT, Categoria TEXT, Valor REAL, DataDespesa TEXT, Observacao TEXT)")
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS Usuarios(ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT UNIQUE, Senha TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Clientes(ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT, Endereco TEXT, Telefone TEXT, ModeloMoto TEXT, AnoMoto TEXT, KM TEXT, Placa TEXT)")
        
        colunas_novas_clientes = ["ModeloMoto", "AnoMoto", "KM", "KMEntrada", "KMSaida", "DataEntrada", "DataSaida", "Placa"]
        for col in colunas_novas_clientes:
            try: cursor.execute(f"ALTER TABLE Clientes ADD COLUMN {col} TEXT")
            except Exception: pass

        cursor.execute("CREATE TABLE IF NOT EXISTS Vendas(ID INTEGER PRIMARY KEY AUTOINCREMENT, ClienteID INTEGER, Servico TEXT, ValorTotal REAL, ValorPago REAL, DataCompra TEXT)")
        
        colunas_novas_vendas = ["FormaPagamento", "Observacao", "CustoInsumos"]
        for col in colunas_novas_vendas:
            try: cursor.execute(f"ALTER TABLE Vendas ADD COLUMN {col} TEXT")
            except Exception: pass

        cursor.execute("CREATE TABLE IF NOT EXISTS Produtos(ID TEXT PRIMARY KEY, NomeProduto TEXT, Descricao TEXT, Preco REAL, QtdEstoque REAL DEFAULT 0.0, UnidadeMedida TEXT DEFAULT 'un', CustoCompra REAL DEFAULT 0.0)")
        
        colunas_novas_produtos = ["QtdEstoque", "UnidadeMedida", "CustoCompra"]
        for col in colunas_novas_produtos:
            try: cursor.execute(f"ALTER TABLE Produtos ADD COLUMN {col} TEXT")
            except Exception: pass

        cursor.execute("CREATE TABLE IF NOT EXISTS Despesas(ID INTEGER PRIMARY KEY AUTOINCREMENT, Descricao TEXT, Categoria TEXT, Valor REAL, DataDespesa TEXT, Observacao TEXT)")

    usuarios_padrao = [('admin', '123'), ('maironxd', '14125'), ('luana', '14125'), ('josue', '123')]
    for user, senha in usuarios_padrao:
        cursor.execute("SELECT * FROM Usuarios WHERE Nome=%s" if DATABASE_URL else "SELECT * FROM Usuarios WHERE Nome=?", (user,))
        if not cursor.fetchone():
            if DATABASE_URL:
                cursor.execute("INSERT INTO Usuarios (Nome, Senha) VALUES (%s, %s)", (user, senha))
            else:
                cursor.execute("INSERT INTO Usuarios VALUES (NULL,?,?)", (user, senha))

    conn.commit()
    conn.close()

init_db()

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lava Rápido Auto Lub - Web</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen flex flex-col">
    {% if session.get('usuario') %}
    <nav class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex justify-between items-center shadow-md">
        <div class="flex items-center space-x-3">
            <i class="fa-solid fa-car-wash text-cyan-400 text-2xl"></i>
            <span class="text-xl font-bold tracking-wide text-cyan-400">Lava Rápido Auto Lub</span>
        </div>
        <div class="flex items-center space-x-6 text-sm font-medium">
            <a href="{{ url_for('index') }}" class="hover:text-cyan-400 transition"><i class="fa-solid fa-boxes-stacked mr-1"></i> Estoque</a>
            <a href="{{ url_for('clientes') }}" class="hover:text-cyan-400 transition"><i class="fa-solid fa-users mr-1"></i> Clientes</a>
            <a href="{{ url_for('despesas') }}" class="hover:text-cyan-400 transition"><i class="fa-solid fa-wallet mr-1"></i> Despesas</a>
            <a href="{{ url_for('dashboard') }}" class="hover:text-cyan-400 transition"><i class="fa-solid fa-chart-line mr-1"></i> Dashboard</a>
            <a href="{{ url_for('logout') }}" class="bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg shadow transition"><i class="fa-solid fa-right-from-bracket mr-1"></i> Sair</a>
        </div>
    </nav>
    {% endif %}

    <main class="flex-1 p-6 max-w-7xl mx-auto w-full">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="mb-4 p-4 rounded-xl text-sm font-semibold shadow-md {% if category == 'error' %}bg-red-900/50 border border-red-700 text-red-200{% else %}bg-emerald-900/50 border border-emerald-700 text-emerald-200{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>
</body>
</html>
"""

LOGIN_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="flex items-center justify-center min-h-[80vh]">
    <div class="bg-slate-900 p-8 rounded-2xl shadow-2xl border border-slate-800 w-full max-w-md">
        <div class="text-center mb-6">
            <i class="fa-solid fa-shield-halved text-cyan-400 text-4xl mb-2"></i>
            <h1 class="text-2xl font-bold text-white">Lava Rápido Auto Lub</h1>
            <p class="text-slate-400 text-sm">Faça login para acessar o sistema</p>
        </div>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Usuário</label>
                <input type="text" name="usuario" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Senha</label>
                <input type="password" name="senha" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg shadow-lg transition duration-200">ENTRAR</button>
        </form>
    </div>
</div>
""")

INDEX_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-boxes-stacked text-cyan-400 mr-2"></i> Gestão de Produtos e Insumos</h1>
        <a href="{{ url_for('novo_produto') }}" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl font-semibold shadow transition flex items-center"><i class="fa-solid fa-plus mr-2"></i> Novo Produto/Insumo</a>
    </div>
    <div class="bg-slate-900 rounded-xl border border-slate-800 shadow overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-950 text-cyan-400 text-xs uppercase tracking-wider border-b border-slate-800">
                    <th class="p-4">Código</th>
                    <th class="p-4">Produto / Insumo</th>
                    <th class="p-4">Preço</th>
                    <th class="p-4">Estoque</th>
                    <th class="p-4 text-center">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for p in produtos %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ p[0] }}</td>
                    <td class="p-4 font-semibold text-white">{{ p[1] }}</td>
                    <td class="p-4 text-slate-300">R$ {{ "%.2f"|format(p[3] or 0.0) }}</td>
                    <td class="p-4 font-bold text-emerald-400">{{ p[4] }} {{ p[5] or 'un' }}</td>
                    <td class="p-4 text-center space-x-2">
                        <a href="{{ url_for('editar_produto', id=p[0]) }}" class="text-blue-400 hover:text-blue-300"><i class="fa-solid fa-pen"></i></a>
                        <a href="{{ url_for('excluir_produto', id=p[0]) }}" onclick="return confirm('Deseja excluir?')" class="text-red-400 hover:text-red-300"><i class="fa-solid fa-trash"></i></a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

CLIENTES_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-users text-cyan-400 mr-2"></i> Gestão de Clientes</h1>
        <a href="{{ url_for('novo_cliente') }}" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl font-semibold shadow transition flex items-center"><i class="fa-solid fa-plus mr-2"></i> Novo Cliente</a>
    </div>
    <div class="bg-slate-900 rounded-xl border border-slate-800 shadow overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-950 text-cyan-400 text-xs uppercase tracking-wider border-b border-slate-800">
                    <th class="p-4">ID</th>
                    <th class="p-4">Nome</th>
                    <th class="p-4">Telefone</th>
                    <th class="p-4">Veículo</th>
                    <th class="p-4">Placa</th>
                    <th class="p-4 text-center">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for c in clientes %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ c[0] }}</td>
                    <td class="p-4 font-semibold text-white">{{ c[1] }}</td>
                    <td class="p-4 text-slate-300">{{ c[3] or '-' }}</td>
                    <td class="p-4 text-slate-300">{{ c[4] or '-' }}</td>
                    <td class="p-4 font-mono text-cyan-400">{{ c[7] or '-' }}</td>
                    <td class="p-4 text-center space-x-2">
                        <a href="{{ url_for('lancamento_servico', cliente_id=c[0]) }}" class="bg-emerald-600/20 text-emerald-400 px-2.5 py-1 rounded-lg text-xs font-bold">Lançar</a>
                        <a href="{{ url_for('historico_cliente', cliente_id=c[0]) }}" class="bg-blue-600/20 text-blue-400 px-2.5 py-1 rounded-lg text-xs font-bold">Histórico</a>
                        <a href="{{ url_for('extrato_cliente', cliente_id=c[0]) }}" class="bg-amber-600/20 text-amber-400 px-2.5 py-1 rounded-lg text-xs font-bold">Extrato Débitos</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

EXTRATO_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6 max-w-4xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
    <div class="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
            <h1 class="text-xl font-bold text-white"><i class="fa-solid fa-file-invoice-dollar text-amber-400 mr-2"></i> Extrato de Débitos</h1>
            <p class="text-slate-400 text-sm mt-1">Cliente: <span class="text-cyan-400 font-semibold">{{ cliente[1] }}</span></p>
        </div>
        <a href="{{ url_for('clientes') }}" class="bg-slate-800 text-slate-300 px-4 py-2 rounded-lg text-sm font-semibold">Voltar</a>
    </div>
    <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
        <p class="text-sm text-slate-400">Total em Aberto:</p>
        <p class="text-3xl font-bold text-red-400 mt-1">R$ {{ "%.2f"|format(total_debitos) }}</p>
    </div>
</div>
""")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuarios WHERE Nome=%s AND Senha=%s" if DATABASE_URL else "SELECT * FROM Usuarios WHERE Nome=? AND Senha=?", (usuario, senha))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['usuario'] = usuario
            return redirect(url_for('index'))
        flash('Usuário ou senha incorretos!', 'error')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Produtos")
    produtos = cursor.fetchall()
    conn.close()
    return render_template_string(INDEX_HTML, produtos=produtos)

@app.route('/clientes')
def clientes():
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clientes")
    clientes = cursor.fetchall()
    conn.close()
    return render_template_string(CLIENTES_HTML, clientes=clientes)

@app.route('/novo_cliente', methods=['GET', 'POST'])
def novo_cliente():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        placa = request.form.get('placa')
        conn = get_db_connection()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute("INSERT INTO Clientes (Nome, Telefone, Placa) VALUES (%s, %s, %s)", (nome, telefone, placa))
        else:
            cursor.execute("INSERT INTO Clientes (ID, Nome, Telefone, Placa) VALUES (NULL, ?, ?, ?)", (nome, telefone, placa))
        conn.commit()
        conn.close()
        return redirect(url_for('clientes'))
    return "<h1>Formulário Novo Cliente Simplificado</h1><a href='/clientes'>Voltar</a>"

@app.route('/lancamento_servico/<int:cliente_id>', methods=['GET', 'POST'])
def lancamento_servico(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    return "<h1>Lançamento de Serviço</h1><a href='/clientes'>Voltar</a>"

@app.route('/historico_cliente/<int:cliente_id>')
def historico_cliente(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    return "<h1>Histórico do Cliente</h1><a href='/clientes'>Voltar</a>"

@app.route('/extrato_cliente/<int:cliente_id>')
def extrato_cliente(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clientes WHERE ID=%s" if DATABASE_URL else "SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()
    conn.close()
    return render_template_string(EXTRATO_HTML, cliente=cliente, total_debitos=0.0)

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    return "<h1>Dashboard em construção</h1><a href='/'>Voltar</a>"

@app.route('/despesas')
def despesas():
    if 'usuario' not in session: return redirect(url_for('login'))
    return "<h1>Despesas</h1><a href='/'>Voltar</a>"

@app.route('/novo_produto', methods=['GET', 'POST'])
def novo_produto():
    return redirect(url_for('index'))

@app.route('/editar_produto/<id>')
def editar_produto(id):
    return redirect(url_for('index'))

@app.route('/excluir_produto/<id>')
def excluir_produto(id):
    return redirect(url_for('index'))

@app.route('/excluir_cliente/<int:id>')
def excluir_cliente(id):
    return redirect(url_for('clientes'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
