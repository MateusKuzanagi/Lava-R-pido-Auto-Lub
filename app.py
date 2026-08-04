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
    # Ajuste para garantir compatibilidade da URL do SQLAlchemy/Render com psycopg2 puro se necessário
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

# TEMPLATES HTML EMBUTIDOS COM DESIGN MODERNO (Tailwind CSS)
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

    <!-- Cards Resumo -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-slate-900 p-5 rounded-xl border border-slate-800 shadow">
            <p class="text-slate-400 text-xs font-bold uppercase">Cadastrados</p>
            <p class="text-2xl font-bold text-white mt-1">{{ total_cadastrados }}</p>
        </div>
        <div class="bg-slate-900 p-5 rounded-xl border border-slate-800 shadow">
            <p class="text-slate-400 text-xs font-bold uppercase">Valor Estoque (Custo)</p>
            <p class="text-2xl font-bold text-emerald-400 mt-1">R$ {{ "%.2f"|format(valor_estoque) }}</p>
        </div>
        <div class="bg-slate-900 p-5 rounded-xl border border-slate-800 shadow">
            <p class="text-slate-400 text-xs font-bold uppercase">Receita do Mês</p>
            <p class="text-2xl font-bold text-cyan-400 mt-1">R$ {{ "%.2f"|format(receita_mes) }}</p>
        </div>
        <div class="bg-slate-900 p-5 rounded-xl border border-slate-800 shadow">
            <p class="text-slate-400 text-xs font-bold uppercase">Estoque Baixo</p>
            <p class="text-2xl font-bold text-red-400 mt-1">{{ estoque_baixo }} itens</p>
        </div>
    </div>

    <!-- Tabela Produtos -->
    <div class="bg-slate-900 rounded-xl border border-slate-800 shadow overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-950 text-cyan-400 text-xs uppercase tracking-wider border-b border-slate-800">
                    <th class="p-4">Código</th>
                    <th class="p-4">Produto / Insumo</th>
                    <th class="p-4">Descrição</th>
                    <th class="p-4">Preço Cobrado</th>
                    <th class="p-4">Estoque Atual</th>
                    <th class="p-4">Valor Lote</th>
                    <th class="p-4 text-center">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for p in produtos %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ p[0] }}</td>
                    <td class="p-4 font-semibold text-white">{{ p[1] }}</td>
                    <td class="p-4 text-slate-400">{{ p[2] or '-' }}</td>
                    <td class="p-4 text-slate-300">R$ {{ "%.2f"|format(p[3] or 0.0) }}</td>
                    <td class="p-4 font-bold {% if p[4] <= 2 %}text-red-400{% else %}text-emerald-400{% endif %}">{{ p[4] }} {{ p[5] or 'un' }}</td>
                    <td class="p-4 text-slate-300">R$ {{ "%.2f"|format(p[6] or 0.0) }}</td>
                    <td class="p-4 text-center space-x-2">
                        <a href="{{ url_for('editar_produto', id=p[0]) }}" class="text-blue-400 hover:text-blue-300 font-semibold"><i class="fa-solid fa-pen"></i></a>
                        <a href="{{ url_for('excluir_produto', id=p[0]) }}" onclick="return confirm('Deseja excluir este item?')" class="text-red-400 hover:text-red-300 font-semibold"><i class="fa-solid fa-trash"></i></a>
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
        <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-users text-cyan-400 mr-2"></i> Gestão de Clientes e Veículos</h1>
        <a href="{{ url_for('novo_cliente') }}" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl font-semibold shadow transition flex items-center"><i class="fa-solid fa-plus mr-2"></i> Novo Cliente</a>
    </div>

    <div class="bg-slate-900 rounded-xl border border-slate-800 shadow overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-950 text-cyan-400 text-xs uppercase tracking-wider border-b border-slate-800">
                    <th class="p-4">ID</th>
                    <th class="p-4">Nome</th>
                    <th class="p-4">Endereço</th>
                    <th class="p-4">Telefone</th>
                    <th class="p-4">Veículo</th>
                    <th class="p-4">Placa</th>
                    <th class="p-4">KM</th>
                    <th class="p-4 text-center">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for c in clientes %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ c[0] }}</td>
                    <td class="p-4 font-semibold text-white">{{ c[1] }}</td>
                    <td class="p-4 text-slate-400">{{ c[2] or '-' }}</td>
                    <td class="p-4 text-slate-300">{{ c[3] or '-' }}</td>
                    <td class="p-4 text-slate-300">{{ c[4] or '-' }}</td>
                    <td class="p-4 font-mono text-cyan-400">{{ c[7] or c[5] or '-' }}</td>
                    <td class="p-4 text-slate-300">{{ c[6] or '-' }}</td>
                    <td class="p-4 text-center space-x-2">
                        <a href="{{ url_for('lancamento_servico', cliente_id=c[0]) }}" class="bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 px-2.5 py-1 rounded-lg text-xs font-bold" title="Lançar Serviço"><i class="fa-solid fa-cash-register"></i></a>
                        <a href="{{ url_for('historico_cliente', cliente_id=c[0]) }}" class="bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 px-2.5 py-1 rounded-lg text-xs font-bold" title="Histórico"><i class="fa-solid fa-clock-rotate-left"></i></a>
                        <a href="{{ url_for('extrato_cliente', cliente_id=c[0]) }}" class="bg-amber-600/20 text-amber-400 hover:bg-amber-600/30 px-2.5 py-1 rounded-lg text-xs font-bold" title="Extrato Débitos"><i class="fa-solid fa-file-invoice-dollar"></i></a>
                        <a href="{{ url_for('relatorio_desempenho', cliente_id=c[0]) }}" class="bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 px-2.5 py-1 rounded-lg text-xs font-bold" title="Desempenho"><i class="fa-solid fa-chart-pie"></i></a>
                        <a href="{{ url_for('editar_cliente', id=c[0]) }}" class="text-blue-400 hover:text-blue-300"><i class="fa-solid fa-pen"></i></a>
                        <a href="{{ url_for('excluir_cliente', id=c[0]) }}" onclick="return confirm('Excluir cliente e histórico?')" class="text-red-400 hover:text-red-300"><i class="fa-solid fa-trash"></i></a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

FORM_PRODUTO_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="max-w-xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
    <h1 class="text-xl font-bold text-white mb-6"><i class="fa-solid fa-box text-cyan-400 mr-2"></i> {{ titulo }}</h1>
    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Código / ID</label>
            <input type="text" name="id" value="{{ p[0] if p else '' }}" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Nome do Produto / Insumo</label>
            <input type="text" name="nome" value="{{ p[1] if p else '' }}" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Descrição</label>
            <input type="text" name="desc" value="{{ p[2] if p else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Preço de Cobrança (R$)</label>
                <input type="number" step="0.01" name="preco" value="{{ p[3] if p else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Quantidade em Estoque</label>
                <input type="number" step="0.01" name="qtd" value="{{ p[4] if p else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Unidade de Medida</label>
                <select name="unidade" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
                    <option value="L (Litros)" {% if p and p[5]=='L (Litros)' %}selected{% endif %}>L (Litros)</option>
                    <option value="ml" {% if p and p[5]=='ml' %}selected{% endif %}>ml</option>
                    <option value="kg" {% if p and p[5]=='kg' %}selected{% endif %}>kg</option>
                    <option value="g" {% if p and p[5]=='g' %}selected{% endif %}>g</option>
                    <option value="un (Unidades)" {% if p and p[5]=='un (Unidades)' %}selected{% endif %}>un (Unidades)</option>
                    <option value="galão" {% if p and p[5]=='galão' %}selected{% endif %}>galão</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Valor do Lote (R$)</label>
                <input type="number" step="0.01" name="custo" value="{{ p[6] if p else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="flex space-x-4 pt-4">
            <button type="submit" class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-lg shadow">Salvar</button>
            <a href="{{ url_for('index') }}" class="flex-1 bg-slate-800 hover:bg-slate-700 text-center py-2.5 rounded-lg text-slate-300 font-bold">Cancelar</a>
        </div>
    </form>
</div>
""")

FORM_CLIENTE_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="max-w-xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
    <h1 class="text-xl font-bold text-white mb-6"><i class="fa-solid fa-user text-cyan-400 mr-2"></i> {{ titulo }}</h1>
    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Nome do Cliente</label>
            <input type="text" name="nome" value="{{ c[1] if c else '' }}" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Endereço</label>
            <input type="text" name="endereco" value="{{ c[2] if c else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Telefone</label>
            <input type="text" name="telefone" value="{{ c[3] if c else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Modelo do Veículo</label>
                <input type="text" name="modelo" value="{{ c[4] if c else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Ano</label>
                <input type="text" name="ano" value="{{ c[5] if c else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Placa</label>
                <input type="text" name="placa" value="{{ c[7] if c else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">KM</label>
                <input type="text" name="km" value="{{ c[6] if c else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Data (DD/MM/AAAA)</label>
                <input type="text" name="data" value="{{ c[10] if c and c|length > 10 and c[10] else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="flex space-x-4 pt-4">
            <button type="submit" class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-lg shadow">Salvar</button>
            <a href="{{ url_for('clientes') }}" class="flex-1 bg-slate-800 hover:bg-slate-700 text-center py-2.5 rounded-lg text-slate-300 font-bold">Cancelar</a>
        </div>
    </form>
</div>
""")

DESPESAS_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-wallet text-orange-400 mr-2"></i> Controle de Despesas</h1>
        <a href="{{ url_for('nova_despesa') }}" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl font-semibold shadow transition flex items-center"><i class="fa-solid fa-plus mr-2"></i> Nova Despesa</a>
    </div>

    <div class="bg-slate-900 rounded-xl border border-slate-800 shadow overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-950 text-orange-400 text-xs uppercase tracking-wider border-b border-slate-800">
                    <th class="p-4">ID</th>
                    <th class="p-4">Descrição</th>
                    <th class="p-4">Categoria</th>
                    <th class="p-4">Valor</th>
                    <th class="p-4">Data</th>
                    <th class="p-4">Observação</th>
                    <th class="p-4 text-center">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for d in despesas %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ d[0] }}</td>
                    <td class="p-4 font-semibold text-white">{{ d[1] }}</td>
                    <td class="p-4 text-slate-400">{{ d[2] }}</td>
                    <td class="p-4 font-bold text-red-400">R$ {{ "%.2f"|format(d[3]) }}</td>
                    <td class="p-4 text-slate-300">{{ d[4] }}</td>
                    <td class="p-4 text-slate-400">{{ d[5] or '-' }}</td>
                    <td class="p-4 text-center">
                        <a href="{{ url_for('excluir_despesa', id=d[0]) }}" onclick="return confirm('Excluir despesa?')" class="text-red-400 hover:text-red-300"><i class="fa-solid fa-trash"></i></a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

FORM_DESPESA_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="max-w-xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
    <h1 class="text-xl font-bold text-white mb-6"><i class="fa-solid fa-receipt text-orange-400 mr-2"></i> Nova Despesa</h1>
    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Descrição</label>
            <input type="text" name="descricao" required placeholder="Ex: Aluguel do Barracão" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Categoria</label>
            <select name="categoria" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
                <option value="Aluguel">Aluguel</option>
                <option value="Água">Água</option>
                <option value="Luz">Luz</option>
                <option value="Internet">Internet</option>
                <option value="Produtos/Limpeza">Produtos/Limpeza</option>
                <option value="Manutenção">Manutenção</option>
                <option value="Outros">Outros</option>
            </select>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Valor (R$)</label>
                <input type="number" step="0.01" name="valor" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Data (DD/MM/AAAA)</label>
                <input type="text" name="data" value="{{ hoje }}" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Observação</label>
            <input type="text" name="obs" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div class="flex space-x-4 pt-4">
            <button type="submit" class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-lg shadow">Salvar Despesa</button>
            <a href="{{ url_for('despesas') }}" class="flex-1 bg-slate-800 hover:bg-slate-700 text-center py-2.5 rounded-lg text-slate-300 font-bold">Cancelar</a>
        </div>
    </form>
</div>
""")

LANCAMENTO_SERVICO_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="max-w-2xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
    <h1 class="text-xl font-bold text-white mb-2"><i class="fa-solid fa-cash-register text-cyan-400 mr-2"></i> Lançar Serviço / Lavagem</h1>
    <p class="text-slate-400 text-sm mb-6">Cliente: <span class="text-cyan-400 font-semibold">{{ cliente[1] }}</span></p>

    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Descrição do Serviço / Lavagem</label>
            <input type="text" name="servico_desc" required placeholder="Ex: Lavagem Completa + Cera" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Valor Total (R$)</label>
                <input type="number" step="0.01" name="valor_total" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Valor Pago (R$)</label>
                <input type="number" step="0.01" name="valor_pago" required class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Forma de Pagamento</label>
                <select name="forma_pagto" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
                    <option value="Pix">Pix</option>
                    <option value="Dinheiro">Dinheiro</option>
                    <option value="Cartão de Crédito">Cartão de Crédito</option>
                    <option value="Cartão de Débito">Cartão de Débito</option>
                    <option value="A prazo">A prazo</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Observação</label>
                <input type="text" name="obs" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="pt-4">
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-lg shadow transition">FINALIZAR LANÇAMENTO</button>
        </div>
    </form>
</div>
""")

HISTORICO_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6">
    <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow flex justify-between items-center">
        <div>
            <h1 class="text-xl font-bold text-white"><i class="fa-solid fa-user text-cyan-400 mr-2"></i> Prontuário: {{ cliente[1] }}</h1>
            <p class="text-slate-400 text-sm mt-1">Tel: {{ cliente[3] or 'N/I' }} | Veículo: {{ cliente[4] or 'N/A' }} (Placa: {{ cliente[7] or 'N/A' }})</p>
        </div>
        <div class="space-x-2">
            <a href="{{ url_for('extrato_cliente', cliente_id=cliente[0]) }}" class="bg-amber-600 hover:bg-amber-700 text-white px-3 py-2 rounded-lg text-sm font-semibold"><i class="fa-solid fa-file-invoice-dollar mr-1"></i> Extrato Débitos</a>
            <a href="{{ url_for('relatorio_desempenho', cliente_id=cliente[0]) }}" class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-2 rounded-lg text-sm font-semibold"><i class="fa-solid fa-chart-pie mr-1"></i> Desempenho</a>
            <a href="{{ url_for('clientes') }}" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-lg text-sm font-semibold">Voltar</a>
        </div>
    </div>

    <div class="bg-slate-900 rounded-xl border border-slate-800 shadow overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-950 text-cyan-400 text-xs uppercase tracking-wider border-b border-slate-800">
                    <th class="p-4">OS #</th>
                    <th class="p-4">Data</th>
                    <th class="p-4">Serviço / Produtos</th>
                    <th class="p-4">Total</th>
                    <th class="p-4">Pago</th>
                    <th class="p-4">Pagamento</th>
                    <th class="p-4">Obs</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for v in vendas %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ v[0] }}</td>
                    <td class="p-4 text-slate-300">{{ v[5] }}</td>
                    <td class="p-4 text-white">{{ v[2] }}</td>
                    <td class="p-4 text-slate-300">R$ {{ "%.2f"|format(v[3] or 0.0) }}</td>
                    <td class="p-4 text-emerald-400">R$ {{ "%.2f"|format(v[4] or 0.0) }}</td>
                    <td class="p-4 text-slate-300">{{ v[6] or '-' }}</td>
                    <td class="p-4 text-slate-400">{{ v[7] or '-' }}</td>
                </tr>
                {% else %}
                <tr><td colspan="7" class="p-6 text-center text-slate-500">Nenhum serviço registrado para este cliente.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

EXTRATO_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Extrato de Débitos - Lava Rápido Auto Lub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @media print {
            .no-print { display: none !important; }
            body { background: white !important; color: black !important; }
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans p-6">
    <div class="max-w-3xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
        <div class="flex justify-between items-center border-b border-slate-800 pb-4 mb-6">
            <div>
                <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-file-invoice-dollar text-cyan-400 mr-2"></i> Extrato de Débitos / Fiado</h1>
                <p class="text-slate-400 text-sm mt-1">Lava Rápido Auto Lub</p>
            </div>
            <div class="no-print">
                <button onclick="window.print()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-bold shadow"><i class="fa-solid fa-print mr-1"></i> Imprimir / PDF</button>
                <a href="{{ url_for('clientes') }}" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm font-semibold ml-2">Voltar</a>
            </div>
        </div>

        <div class="mb-6 bg-slate-950 p-4 rounded-xl border border-slate-800">
            <p class="text-sm text-slate-400">Cliente: <strong class="text-white">{{ cliente[1] }}</strong></p>
            <p class="text-sm text-slate-400">Telefone: <strong class="text-white">{{ cliente[3] or 'N/I' }}</strong></p>
            <p class="text-sm text-slate-400">Veículo / Placa: <strong class="text-white">{{ cliente[4] or 'N/A' }} ({{ cliente[7] or 'N/A' }})</strong></p>
        </div>

        <div class="overflow-hidden rounded-xl border border-slate-800 mb-6">
            <table class="w-full text-left border-collapse text-sm">
                <thead>
                    <tr class="bg-slate-950 text-cyan-400 uppercase text-xs border-b border-slate-800">
                        <th class="p-3">OS #</th>
                        <th class="p-3">Data</th>
                        <th class="p-3">Serviço</th>
                        <th class="p-3">Total</th>
                        <th class="p-3">Pago</th>
                        <th class="p-3">Pendente</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
                    {% for d in debitos %}
                    {% set pendente = (d[3] or 0.0) - (d[4] or 0.0) %}
                    <tr class="hover:bg-slate-800/30">
                        <td class="p-3 font-mono text-cyan-300">{{ d[0] }}</td>
                        <td class="p-3">{{ d[5] }}</td>
                        <td class="p-3">{{ d[2] }}</td>
                        <td class="p-3">R$ {{ "%.2f"|format(d[3] or 0.0) }}</td>
                        <td class="p-3 text-emerald-400">R$ {{ "%.2f"|format(d[4] or 0.0) }}</td>
                        <td class="p-3 font-bold text-red-400">R$ {{ "%.2f"|format(pendente) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="6" class="p-6 text-center text-slate-500">Nenhum débito ou pendência em aberto para este cliente.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 flex justify-between items-center">
            <span class="text-lg font-bold text-slate-300">Total Geral em Aberto:</span>
            <span class="text-2xl font-bold text-red-400">R$ {{ "%.2f"|format(total_devedor) }}</span>
        </div>
    </div>
</body>
</html>
"""

RELATORIO_DESEMPENHO_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Desempenho - Lava Rápido Auto Lub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @media print {
            .no-print { display: none !important; }
            body { background: white !important; color: black !important; }
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans p-6">
    <div class="max-w-4xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
        <div class="flex justify-between items-center border-b border-slate-800 pb-4 mb-6">
            <div>
                <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-chart-pie text-cyan-400 mr-2"></i> Relatório de Desempenho do Cliente</h1>
                <p class="text-slate-400 text-sm mt-1">Lava Rápido Auto Lub</p>
            </div>
            <div class="no-print">
                <button onclick="window.print()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-sm font-bold shadow"><i class="fa-solid fa-print mr-1"></i> Imprimir / PDF</button>
                <a href="{{ url_for('clientes') }}" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm font-semibold ml-2">Voltar</a>
            </div>
        </div>

        <div class="mb-6 bg-slate-950 p-4 rounded-xl border border-slate-800">
            <p class="text-sm text-slate-400">Cliente: <strong class="text-white">{{ cliente[1] }}</strong> | Telefone: <strong class="text-white">{{ cliente[3] or 'N/I' }}</strong></p>
            <p class="text-sm text-slate-400 mt-1">Veículo: <strong class="text-white">{{ cliente[4] or 'N/A' }}</strong> | Placa: <strong class="text-white">{{ cliente[7] or 'N/A' }}</strong></p>
        </div>

        <!-- Cards de Indicadores -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center">
                <p class="text-xs text-slate-400 uppercase font-bold">Total de Visitas</p>
                <p class="text-2xl font-bold text-cyan-400 mt-1">{{ total_visitas }}</p>
            </div>
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center">
                <p class="text-xs text-slate-400 uppercase font-bold">Valor Total Gasto</p>
                <p class="text-2xl font-bold text-emerald-400 mt-1">R$ {{ "%.2f"|format(total_gasto) }}</p>
            </div>
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center">
                <p class="text-xs text-slate-400 uppercase font-bold">Média por Visita</p>
                <p class="text-2xl font-bold text-blue-400 mt-1">R$ {{ "%.2f"|format(media_gasto) }}</p>
            </div>
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center">
                <p class="text-xs text-slate-400 uppercase font-bold">Última Visita</p>
                <p class="text-lg font-bold text-amber-400 mt-1">{{ ultima_visita or 'Nunca' }}</p>
            </div>
        </div>

        <h3 class="text-lg font-bold text-white mb-3">Histórico Completo de Serviços</h3>
        <div class="overflow-hidden rounded-xl border border-slate-800">
            <table class="w-full text-left border-collapse text-sm">
                <thead>
                    <tr class="bg-slate-950 text-cyan-400 uppercase text-xs border-b border-slate-800">
                        <th class="p-3">Data</th>
                        <th class="p-3">Serviço Realizado</th>
                        <th class="p-3">Forma Pagto</th>
                        <th class="p-3">Valor Total</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
                    {% for s in servicos %}
                    <tr class="hover:bg-slate-800/30">
                        <td class="p-3">{{ s[5] }}</td>
                        <td class="p-3 text-white font-medium">{{ s[2] }}</td>
                        <td class="p-3 text-slate-300">{{ s[6] or '-' }}</td>
                        <td class="p-3 font-bold text-emerald-400">R$ {{ "%.2f"|format(s[3] or 0.0) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" class="p-6 text-center text-slate-500">Nenhum serviço registrado para este cliente.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6">
    <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-chart-line text-cyan-400 mr-2"></i> Dashboard Financeiro</h1>
    <div class="bg-slate-900 p-8 rounded-xl border border-slate-800 shadow text-center space-y-4">
        <p class="text-slate-400 text-lg">Resumo Financeiro Consolidado</p>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
            <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                <p class="text-slate-400 text-sm">Receita Total</p>
                <p class="text-3xl font-bold text-cyan-400 mt-2">R$ {{ "%.2f"|format(tot_vendas) }}</p>
            </div>
            <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                <p class="text-slate-400 text-sm">Despesas Totais</p>
                <p class="text-3xl font-bold text-red-400 mt-2">R$ {{ "%.2f"|format(tot_despesas) }}</p>
            </div>
            <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                <p class="text-slate-400 text-sm">Lucro Líquido</p>
                <p class="text-3xl font-bold text-emerald-400 mt-2">R$ {{ "%.2f"|format(tot_vendas - tot_despesas) }}</p>
            </div>
        </div>
    </div>
</div>
""")

# ROTAS DO FLASK
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('usuario')
        senha = request.form.get('senha')
        conn = get_db_connection()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute("SELECT * FROM Usuarios WHERE Nome=%s AND Senha=%s", (user, senha))
        else:
            cursor.execute("SELECT * FROM Usuarios WHERE Nome=? AND Senha=?", (user, senha))
        u = cursor.fetchone()
        conn.close()
        if u:
            session['usuario'] = user
            return redirect(url_for('index'))
        flash('Credenciais incorretas!', 'error')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Produtos")
    produtos = cursor.fetchall()

    cursor.execute("SELECT SUM(ValorPago) FROM Vendas")
    res_vendas = cursor.fetchone()
    receita_mes = res_vendas[0] if res_vendas and res_vendas[0] else 0.0

    total_cadastrados = len(produtos)
    valor_estoque = sum((p[4] or 0.0) * (p[6] or 0.0) for p in produtos)
    estoque_baixo = sum(1 for p in produtos if (p[4] or 0.0) <= 2)
    conn.close()

    return render_template_string(INDEX_HTML, produtos=produtos, total_cadastrados=total_cadastrados, valor_estoque=valor_estoque, receita_mes=receita_mes, estoque_baixo=estoque_baixo)

@app.route('/clientes')
def clientes():
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Clientes")
    clientes_list = cursor.fetchall()
    conn.close()
    return render_template_string(CLIENTES_HTML, clientes=clientes_list)

@app.route('/novo_cliente', methods=['GET', 'POST'])
def novo_cliente():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        endereco = request.form.get('endereco')
        telefone = request.form.get('telefone')
        modelo = request.form.get('modelo')
        ano = request.form.get('ano')
        placa = request.form.get('placa')
        km = request.form.get('km')
        data = request.form.get('data') or datetime.now().strftime('%d/%m/%Y')

        conn = get_db_connection()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute("INSERT INTO Clientes (Nome, Endereco, Telefone, ModeloMoto, AnoMoto, KM, Placa, DataEntrada) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (nome, endereco, telefone, modelo, ano, km, placa, data))
        else:
            cursor.execute("INSERT INTO Clientes (Nome, Endereco, Telefone, ModeloMoto, AnoMoto, KM, Placa, DataEntrada) VALUES (?,?,?,?,?,?,?,?)", (nome, endereco, telefone, modelo, ano, km, placa, data))
        conn.commit()
        conn.close()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('clientes'))
    return render_template_string(FORM_CLIENTE_HTML, c=None, titulo="Novo Cliente")

@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form.get('nome')
        endereco = request.form.get('endereco')
        telefone = request.form.get('telefone')
        modelo = request.form.get('modelo')
        ano = request.form.get('ano')
        placa = request.form.get('placa')
        km = request.form.get('km')
        data = request.form.get('data')

        if DATABASE_URL:
            cursor.execute("UPDATE Clientes SET Nome=%s, Endereco=%s, Telefone=%s, ModeloMoto=%s, AnoMoto=%s, Placa=%s, KM=%s, DataEntrada=%s WHERE ID=%s", (nome, endereco, telefone, modelo, ano, placa, km, data, id))
        else:
            cursor.execute("UPDATE Clientes SET Nome=?, Endereco=?, Telefone=?, ModeloMoto=?, AnoMoto=?, Placa=?, KM=?, DataEntrada=? WHERE ID=?", (nome, endereco, telefone, modelo, ano, placa, km, data, id))
        conn.commit()
        conn.close()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('clientes'))

    if DATABASE_URL:
        cursor.execute("SELECT * FROM Clientes WHERE ID=%s", (id,))
    else:
        cursor.execute("SELECT * FROM Clientes WHERE ID=?", (id,))
    c = cursor.fetchone()
    conn.close()
    return render_template_string(FORM_CLIENTE_HTML, c=c, titulo="Editar Cliente")

@app.route('/excluir_cliente/<int:id>')
def excluir_cliente(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("DELETE FROM Clientes WHERE ID=%s", (id,))
        cursor.execute("DELETE FROM Vendas WHERE ClienteID=%s", (id,))
    else:
        cursor.execute("DELETE FROM Clientes WHERE ID=?", (id,))
        cursor.execute("DELETE FROM Vendas WHERE ClienteID=?", (id,))
    conn.commit()
    conn.close()
    flash('Cliente excluído com sucesso!', 'success')
    return redirect(url_for('clientes'))

@app.route('/lancamento_servico/<int:cliente_id>', methods=['GET', 'POST'])
def lancamento_servico(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("SELECT * FROM Clientes WHERE ID=%s", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()

    if request.method == 'POST':
        servico_desc = request.form.get('servico_desc')
        valor_total = float(request.form.get('valor_total') or 0.0)
        valor_pago = float(request.form.get('valor_pago') or 0.0)
        forma_pagto = request.form.get('forma_pagto')
        obs = request.form.get('obs')
        data_compra = datetime.now().strftime('%d/%m/%Y %H:%M')

        if DATABASE_URL:
            cursor.execute("INSERT INTO Vendas (ClienteID, Servico, ValorTotal, ValorPago, DataCompra, FormaPagamento, Observacao) VALUES (%s, %s, %s, %s, %s, %s, %s)", (cliente_id, servico_desc, valor_total, valor_pago, data_compra, forma_pagto, obs))
        else:
            cursor.execute("INSERT INTO Vendas (ClienteID, Servico, ValorTotal, ValorPago, DataCompra, FormaPagamento, Observacao) VALUES (?,?,?,?,?,?,?)", (cliente_id, servico_desc, valor_total, valor_pago, data_compra, forma_pagto, obs))
        conn.commit()
        conn.close()
        flash('Serviço lançado com sucesso!', 'success')
        return redirect(url_for('clientes'))

    conn.close()
    return render_template_string(LANCAMENTO_SERVICO_HTML, cliente=cliente)

@app.route('/historico/<int:cliente_id>')
def historico_cliente(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("SELECT * FROM Clientes WHERE ID=%s", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()

    if DATABASE_URL:
        cursor.execute("SELECT * FROM Vendas WHERE ClienteID=%s ORDER BY ID DESC", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Vendas WHERE ClienteID=? ORDER BY ID DESC", (cliente_id,))
    vendas = cursor.fetchall()
    conn.close()
    return render_template_string(HISTORICO_HTML, cliente=cliente, vendas=vendas)

@app.route('/extrato/<int:cliente_id>')
def extrato_cliente(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("SELECT * FROM Clientes WHERE ID=%s", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()

    if DATABASE_URL:
        cursor.execute("SELECT * FROM Vendas WHERE ClienteID=%s ORDER BY ID DESC", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Vendas WHERE ClienteID=? ORDER BY ID DESC", (cliente_id,))
    vendas = cursor.fetchall()
    conn.close()

    # Considera débito o que foi vendido mas ainda não totalmente pago
    debitos = [v for v in vendas if (v[3] or 0.0) > (v[4] or 0.0)]
    total_devedor = sum((v[3] or 0.0) - (v[4] or 0.0) for v in debitos)

    return render_template_string(EXTRATO_HTML, cliente=cliente, debitos=debitos, total_devedor=total_devedor)

@app.route('/relatorio-desempenho/<int:cliente_id>')
def relatorio_desempenho(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("SELECT * FROM Clientes WHERE ID=%s", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()

    if DATABASE_URL:
        cursor.execute("SELECT * FROM Vendas WHERE ClienteID=%s ORDER BY ID DESC", (cliente_id,))
    else:
        cursor.execute("SELECT * FROM Vendas WHERE ClienteID=? ORDER BY ID DESC", (cliente_id,))
    servicos = cursor.fetchall()
    conn.close()

    total_gasto = sum((s[3] or 0.0) for s in servicos)
    total_visitas = len(servicos)
    media_gasto = total_gasto / total_visitas if total_visitas > 0 else 0.0
    ultima_visita = servicos[0][5] if servicos and len(servicos[0]) > 5 else None

    return render_template_string(RELATORIO_DESEMPENHO_HTML, cliente=cliente, servicos=servicos, total_gasto=total_gasto, total_visitas=total_visitas, media_gasto=media_gasto, ultima_visita=ultima_visita)

@app.route('/novo_produto', methods=['GET', 'POST'])
def novo_produto():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        pid = request.form.get('id')
        nome = request.form.get('nome')
        desc = request.form.get('desc')
        preco = float(request.form.get('preco') or 0.0)
        qtd = float(request.form.get('qtd') or 0.0)
        unidade = request.form.get('unidade')
        custo = float(request.form.get('custo') or 0.0)

        conn = get_db_connection()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute("INSERT INTO Produtos (ID, NomeProduto, Descricao, Preco, QtdEstoque, UnidadeMedida, CustoCompra) VALUES (%s, %s, %s, %s, %s, %s, %s)", (pid, nome, desc, preco, qtd, unidade, custo))
        else:
            cursor.execute("INSERT INTO Produtos VALUES (?,?,?,?,?,?,?)", (pid, nome, desc, preco, qtd, unidade, custo))
        conn.commit()
        conn.close()
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template_string(FORM_PRODUTO_HTML, p=None, titulo="Novo Produto / Insumo")

@app.route('/editar_produto/<id>', methods=['GET', 'POST'])
def editar_produto(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form.get('nome')
        desc = request.form.get('desc')
        preco = float(request.form.get('preco') or 0.0)
        qtd = float(request.form.get('qtd') or 0.0)
        unidade = request.form.get('unidade')
        custo = float(request.form.get('custo') or 0.0)

        if DATABASE_URL:
            cursor.execute("UPDATE Produtos SET NomeProduto=%s, Descricao=%s, Preco=%s, QtdEstoque=%s, UnidadeMedida=%s, CustoCompra=%s WHERE ID=%s", (nome, desc, preco, qtd, unidade, custo, id))
        else:
            cursor.execute("UPDATE Produtos SET NomeProduto=?, Descricao=?, Preco=?, QtdEstoque=?, UnidadeMedida=?, CustoCompra=? WHERE ID=?", (nome, desc, preco, qtd, unidade, custo, id))
        conn.commit()
        conn.close()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('index'))

    if DATABASE_URL:
        cursor.execute("SELECT * FROM Produtos WHERE ID=%s", (id,))
    else:
        cursor.execute("SELECT * FROM Produtos WHERE ID=?", (id,))
    p = cursor.fetchone()
    conn.close()
    return render_template_string(FORM_PRODUTO_HTML, p=p, titulo="Editar Produto / Insumo")

@app.route('/excluir_produto/<id>')
def excluir_produto(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("DELETE FROM Produtos WHERE ID=%s", (id,))
    else:
        cursor.execute("DELETE FROM Produtos WHERE ID=?", (id,))
    conn.commit()
    conn.close()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/despesas')
def despesas():
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Despesas")
    despesas_list = cursor.fetchall()
    conn.close()
    return render_template_string(DESPESAS_HTML, despesas=despesas_list)

@app.route('/nova_despesa', methods=['GET', 'POST'])
def nova_despesa():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        desc = request.form.get('descricao')
        cat = request.form.get('categoria')
        valor = float(request.form.get('valor') or 0.0)
        data = request.form.get('data')
        obs = request.form.get('obs')

        conn = get_db_connection()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute("INSERT INTO Despesas (Descricao, Categoria, Valor, DataDespesa, Observacao) VALUES (%s, %s, %s, %s, %s)", (desc, cat, valor, data, obs))
        else:
            cursor.execute("INSERT INTO Despesas (Descricao, Categoria, Valor, DataDespesa, Observacao) VALUES (?,?,?,?,?)", (desc, cat, valor, data, obs))
        conn.commit()
        conn.close()
        flash('Despesa cadastrada com sucesso!', 'success')
        return redirect(url_for('despesas'))
    hoje = datetime.now().strftime('%d/%m/%Y')
    return render_template_string(FORM_DESPESA_HTML, hoje=hoje)

@app.route('/excluir_despesa/<int:id>')
def excluir_despesa(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute("DELETE FROM Despesas WHERE ID=%s", (id,))
    else:
        cursor.execute("DELETE FROM Despesas WHERE ID=?", (id,))
    conn.commit()
    conn.close()
    flash('Despesa excluída com sucesso!', 'success')
    return redirect(url_for('despesas'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(ValorPago) FROM Vendas")
    res_v = cursor.fetchone()
    tot_vendas = res_v[0] if res_v and res_v[0] else 0.0

    cursor.execute("SELECT SUM(Valor) FROM Despesas")
    res_d = cursor.fetchone()
    tot_despesas = res_d[0] if res_d and res_d[0] else 0.0

    conn.close()
    return render_template_string(DASHBOARD_HTML, tot_vendas=tot_vendas, tot_despesas=tot_despesas)

if __name__ == '__main__':
    app.run(debug=True)
