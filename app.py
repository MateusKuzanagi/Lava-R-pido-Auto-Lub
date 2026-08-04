from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
import sqlite3
from datetime import datetime
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.secret_key = 'lava_rapido_secret_key_autolub'
BANCO_DADOS = "LavaRapidoAutoLub.db"

def init_db():
    conexao = sqlite3.connect(BANCO_DADOS, timeout=30)
    cursor = conexao.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS Usuarios(ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT UNIQUE, Senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS Clientes(ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT, Endereco TEXT, Telefone TEXT, ModeloMoto TEXT, AnoMoto TEXT, KM TEXT, Placa TEXT)")
    
    colunas_novas_clientes = ["ModeloMoto", "AnoMoto", "KM", "KMEntrada", "KMSaida", "DataEntrada", "DataSaida", "Placa"]
    for col in colunas_novas_clientes:
        try: cursor.execute(f"ALTER TABLE Clientes ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError: pass

    cursor.execute("CREATE TABLE IF NOT EXISTS Vendas(ID INTEGER PRIMARY KEY AUTOINCREMENT, ClienteID INTEGER, Servico TEXT, ValorTotal REAL, ValorPago REAL, DataCompra TEXT)")
    
    colunas_novas_vendas = ["FormaPagamento", "Observacao", "CustoInsumos"]
    for col in colunas_novas_vendas:
        try: cursor.execute(f"ALTER TABLE Vendas ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError: pass

    cursor.execute("CREATE TABLE IF NOT EXISTS Produtos(ID TEXT PRIMARY KEY, NomeProduto TEXT, Descricao TEXT, Preco REAL, QtdEstoque REAL DEFAULT 0.0, UnidadeMedida TEXT DEFAULT 'un', CustoCompra REAL DEFAULT 0.0)")
    
    colunas_novas_produtos = ["QtdEstoque", "UnidadeMedida", "CustoCompra"]
    for col in colunas_novas_produtos:
        try: cursor.execute(f"ALTER TABLE Produtos ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError: pass

    cursor.execute("CREATE TABLE IF NOT EXISTS Despesas(ID INTEGER PRIMARY KEY AUTOINCREMENT, Descricao TEXT, Categoria TEXT, Valor REAL, DataDespesa TEXT, Observacao TEXT)")

    usuarios_padrao = [('admin', '123'), ('maironxd', '14125'), ('luana', '14125'), ('josue', '123')]
    for user, senha in usuarios_padrao:
        cursor.execute("SELECT * FROM Usuarios WHERE Nome=?", (user,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO Usuarios VALUES (NULL,?,?)", (user, senha))

    conexao.commit()
    conexao.close()

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
                    <td class="p-4 font-mono text-cyan-400">{{ c[5] or '-' }}</td>
                    <td class="p-4 text-slate-300">{{ c[6] or '-' }}</td>
                    <td class="p-4 text-center space-x-2">
                        <a href="{{ url_for('lancamento_servico', cliente_id=c[0]) }}" class="bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 px-3 py-1 rounded-lg text-xs font-bold" title="Lançar Serviço"><i class="fa-solid fa-cash-register"></i> Serviço</a>
                        <a href="{{ url_for('historico_cliente', cliente_id=c[0]) }}" class="bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 px-3 py-1 rounded-lg text-xs font-bold" title="Histórico"><i class="fa-solid fa-clock-rotate-left"></i> Histórico</a>
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
                <input type="text" name="data" value="{{ c[8] if c and c|length > 8 and c[8] else '' }}" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
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
<div class="max-w-3xl mx-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl">
    <h1 class="text-xl font-bold text-white mb-2"><i class="fa-solid fa-cash-register text-cyan-400 mr-2"></i> Lançar Serviço e Selecionar Produtos</h1>
    <p class="text-slate-400 text-sm mb-6">Cliente: <span class="text-cyan-400 font-semibold">{{ cliente[1] }}</span></p>

    <form method="POST" class="space-y-6">
        <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Descrição Geral do Serviço / Observação da OS</label>
            <input type="text" name="servico_desc" required placeholder="Ex: Lavagem completa + Troca de Óleo" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
        </div>

        <!-- Seletor dinâmico de múltiplos produtos por código -->
        <div class="space-y-3 bg-slate-950 p-4 rounded-xl border border-slate-800">
            <h3 class="text-sm font-bold text-cyan-400 uppercase tracking-wide"><i class="fa-solid fa-boxes-stacked mr-1"></i> Adicionar Produtos/Insumos por Código</h3>
            <div id="itens-container" class="space-y-3">
                <div class="flex gap-2 items-center item-row">
                    <select name="produto_codigo[]" class="flex-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm">
                        <option value="">Selecione um produto/serviço...</option>
                        {% for p in produtos %}
                        <option value="{{ p[0] }}">[{{ p[0] }}] {{ p[1] }} - R$ {{ "%.2f"|format(p[3] or 0.0) }} (Estoque: {{ p[4] }})</option>
                        {% endfor %}
                    </select>
                    <input type="number" step="0.01" name="produto_qtd[]" placeholder="Qtd" value="1" class="w-24 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm">
                    <button type="button" onclick="removerLinha(this)" class="bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white px-3 py-2 rounded-lg text-sm transition"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
            <button type="button" onclick="adicionarLinha()" class="mt-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold transition"><i class="fa-solid fa-plus mr-1"></i> Adicionar Outro Item</button>
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
                <label class="block text-sm font-medium text-slate-300 mb-1">Observações Adicionais</label>
                <input type="text" name="obs" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
        </div>
        <div class="pt-4">
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-lg shadow transition">FINALIZAR LANÇAMENTO E DAR BAIXA</button>
        </div>
    </form>
</div>

<script>
function adicionarLinha() {
    const container = document.getElementById('itens-container');
    const primeiraLinha = container.querySelector('.item-row');
    const novaLinha = primeiraLinha.cloneNode(true);
    novaLinha.querySelector('input').value = '1';
    novaLinha.querySelector('select').selectedIndex = 0;
    container.appendChild(novaLinha);
}
function removerLinha(btn) {
    const container = document.getElementById('itens-container');
    if (container.querySelectorAll('.item-row').length > 1) {
        btn.closest('.item-row').remove();
    } else {
        alert('Você deve manter pelo menos uma linha de item.');
    }
}
</script>
""")

HISTORICO_HTML = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
<div class="space-y-6">
    <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow flex justify-between items-center">
        <div>
            <h1 class="text-xl font-bold text-white"><i class="fa-solid fa-user text-cyan-400 mr-2"></i> Prontuário: {{ cliente[1] }}</h1>
            <p class="text-slate-400 text-sm mt-1">Tel: {{ cliente[3] or 'N/I' }} | Veículo: {{ cliente[4] or 'N/A' }} (Placa: {{ cliente[7] or 'N/A' }})</p>
        </div>
        <div class="space-x-2">
            <a href="{{ url_for('gerar_pdf_cliente', cliente_id=cliente[0]) }}" class="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition inline-flex items-center"><i class="fa-solid fa-file-pdf mr-2"></i> Baixar Extrato/Débito PDF</a>
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
                    <th class="p-4">Débito / Saldo</th>
                    <th class="p-4">Pagamento</th>
                    <th class="p-4 text-center">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-sm">
                {% for v in vendas %}
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="p-4 font-mono text-cyan-300">{{ v[0] }}</td>
                    <td class="p-4 text-slate-300">{{ v[5] }}</td>
                    <td class="p-4 text-white">{{ v[2] }}</td>
                    <td class="p-4 text-slate-300">R$ {{ "%.2f"|format(v[3]) }}</td>
                    <td class="p-4 text-emerald-400 font-semibold">R$ {{ "%.2f"|format(v[4]) }}</td>
                    <td class="p-4 font-bold {% if (v[3] - v[4]) > 0 %}text-red-400{% else %}text-slate-400{% endif %}">R$ {{ "%.2f"|format(v[3] - v[4]) }}</td>
                    <td class="p-4 text-slate-300">{{ v[6] or '-' }}</td>
                    <td class="p-4 text-center">
                        <a href="{{ url_for('excluir_venda', id=v[0]) }}" onclick="return confirm('Excluir esta OS?')" class="text-red-400 hover:text-red-300"><i class="fa-solid fa-trash"></i></a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

# ROTAS PRINCIPAIS DO FLASK COM A CORREÇÃO DO VALOR DO ESTOQUE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        conexao = sqlite3.connect(BANCO_DADOS)
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM Usuarios WHERE Nome=? AND Senha=?", (usuario, senha))
        user = cursor.fetchone()
        conexao.close()
        if user:
            session['usuario'] = usuario
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos!', 'error')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    
    # CORREÇÃO APLICADA AQUI: Soma correta do valor do estoque (CustoCompra)
    cursor.execute("SELECT SUM(CustoCompra) FROM Produtos")
    res_estoque = cursor.fetchone()
    valor_estoque = res_estoque[0] if res_estoque and res_estoque[0] else 0.0

    cursor.execute("SELECT COUNT(*) FROM Produtos")
    total_cadastrados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Produtos WHERE QtdEstoque <= 2")
    estoque_baixo = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(ValorPago) FROM Vendas")
    res_receita = cursor.fetchone()
    receita_mes = res_receita[0] if res_receita and res_receita[0] else 0.0

    cursor.execute("SELECT ID, NomeProduto, Descricao, Preco, QtdEstoque, UnidadeMedida, CustoCompra FROM Produtos")
    produtos = cursor.fetchall()

    conexao.close()

    return render_template_string(INDEX_HTML, 
                                  produtos=produtos, 
                                  total_cadastrados=total_cadastrados,
                                  valor_estoque=valor_estoque,
                                  receita_mes=receita_mes,
                                  estoque_baixo=estoque_baixo)

@app.route('/produto/novo', methods=['GET', 'POST'])
def novo_produto():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        id_prod = request.form['id']
        nome = request.form['nome']
        desc = request.form['desc']
        preco = float(request.form['preco'] or 0)
        qtd = float(request.form['qtd'] or 0)
        unidade = request.form['unidade']
        custo = float(request.form['custo'] or 0)

        conexao = sqlite3.connect(BANCO_DADOS)
        cursor = conexao.cursor()
        try:
            cursor.execute("INSERT INTO Produtos VALUES (?, ?, ?, ?, ?, ?, ?)", (id_prod, nome, desc, preco, qtd, unidade, custo))
            conexao.commit()
            flash('Produto cadastrado com sucesso!', 'success')
        except sqlite3.IntegrityError:
            flash('Erro: Já existe um produto com este código!', 'error')
        conexao.close()
        return redirect(url_for('index'))
    return render_template_string(FORM_PRODUTO_HTML, titulo="Novo Produto / Insumo", p=None)

@app.route('/produto/editar/<id>', methods=['GET', 'POST'])
def editar_produto(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        desc = request.form['desc']
        preco = float(request.form['preco'] or 0)
        qtd = float(request.form['qtd'] or 0)
        unidade = request.form['unidade']
        custo = float(request.form['custo'] or 0)

        cursor.execute("UPDATE Produtos SET NomeProduto=?, Descricao=?, Preco=?, QtdEstoque=?, UnidadeMedida=?, CustoCompra=? WHERE ID=?", 
                       (nome, desc, preco, qtd, unidade, custo, id))
        conexao.commit()
        conexao.close()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('index'))
    
    cursor.execute("SELECT ID, NomeProduto, Descricao, Preco, QtdEstoque, UnidadeMedida, CustoCompra FROM Produtos WHERE ID=?", (id,))
    p = cursor.fetchone()
    conexao.close()
    return render_template_string(FORM_PRODUTO_HTML, titulo="Editar Produto / Insumo", p=p)

@app.route('/produto/excluir/<id>')
def excluir_produto(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM Produtos WHERE ID=?", (id,))
    conexao.commit()
    conexao.close()
    flash('Produto excluído!', 'success')
    return redirect(url_for('index'))

@app.route('/clientes')
def clientes():
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT ID, Nome, Endereco, Telefone, ModeloMoto, Placa, KM FROM Clientes")
    clientes = cursor.fetchall()
    conexao.close()
    return render_template_string(CLIENTES_HTML, clientes=clientes)

@app.route('/cliente/novo', methods=['GET', 'POST'])
def novo_cliente():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        modelo = request.form['modelo']
        ano = request.form['ano']
        placa = request.form['placa']
        km = request.form['km']
        data = request.form['data']

        conexao = sqlite3.connect(BANCO_DADOS)
        cursor = conexao.cursor()
        cursor.execute("INSERT INTO Clientes (Nome, Endereco, Telefone, ModeloMoto, AnoMoto, Placa, KM, DataEntrada) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (nome, endereco, telefone, modelo, ano, placa, km, data))
        conexao.commit()
        conexao.close()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('clientes'))
    return render_template_string(FORM_CLIENTE_HTML, titulo="Novo Cliente", c=None)

@app.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        modelo = request.form['modelo']
        ano = request.form['ano']
        placa = request.form['placa']
        km = request.form['km']
        data = request.form['data']

        cursor.execute("UPDATE Clientes SET Nome=?, Endereco=?, Telefone=?, ModeloMoto=?, AnoMoto=?, Placa=?, KM=?, DataEntrada=? WHERE ID=?",
                       (nome, endereco, telefone, modelo, ano, placa, km, data, id))
        conexao.commit()
        conexao.close()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('clientes'))

    cursor.execute("SELECT ID, Nome, Endereco, Telefone, ModeloMoto, AnoMoto, KM, Placa, DataEntrada FROM Clientes WHERE ID=?", (id,))
    c = cursor.fetchone()
    conexao.close()
    return render_template_string(FORM_CLIENTE_HTML, titulo="Editar Cliente", c=c)

@app.route('/cliente/excluir/<int:id>')
def excluir_cliente(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM Clientes WHERE ID=?", (id,))
    cursor.execute("DELETE FROM Vendas WHERE ClienteID=?", (id,))
    conexao.commit()
    conexao.close()
    flash('Cliente e histórico removidos!', 'success')
    return redirect(url_for('clientes'))

@app.route('/despesas')
def despesas():
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT ID, Descricao, Categoria, Valor, DataDespesa, Observacao FROM Despesas")
    despesas = cursor.fetchall()
    conexao.close()
    return render_template_string(DESPESAS_HTML, despesas=despesas)

@app.route('/despesa/nova', methods=['GET', 'POST'])
def nova_despesa():
    if 'usuario' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        desc = request.form['descricao']
        cat = request.form['categoria']
        valor = float(request.form['valor'] or 0)
        data = request.form['data']
        obs = request.form['obs']

        conexao = sqlite3.connect(BANCO_DADOS)
        cursor = conexao.cursor()
        cursor.execute("INSERT INTO Despesas (Descricao, Categoria, Valor, DataDespesa, Observacao) VALUES (?, ?, ?, ?, ?)",
                       (desc, cat, valor, data, obs))
        conexao.commit()
        conexao.close()
        flash('Despesa registrada com sucesso!', 'success')
        return redirect(url_for('despesas'))
    hoje = datetime.now().strftime("%d/%m/%Y")
    return render_template_string(FORM_DESPESA_HTML, hoje=hoje)

@app.route('/despesa/excluir/<int:id>')
def excluir_despesa(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM Despesas WHERE ID=?", (id,))
    conexao.commit()
    conexao.close()
    flash('Despesa excluída!', 'success')
    return redirect(url_for('despesas'))

@app.route('/cliente/servico/<int:cliente_id>', methods=['GET', 'POST'])
def lancamento_servico(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()

    if request.method == 'POST':
        servico_desc = request.form['servico_desc']
        valor_total = float(request.form['valor_total'] or 0)
        valor_pago = float(request.form['valor_pago'] or 0)
        forma_pagto = request.form['forma_pagto']
        obs = request.form['obs']
        data_compra = datetime.now().strftime("%d/%m/%Y")

        produtos_cod = request.form.getlist('produto_codigo[]')
        produtos_qtd = request.form.getlist('produto_qtd[]')

        for cod, qtd_str in zip(produtos_cod, produtos_qtd):
            if cod:
                try:
                    qtd_usada = float(qtd_str or 0)
                    cursor.execute("UPDATE Produtos SET QtdEstoque = QtdEstoque - ? WHERE ID = ?", (qtd_usada, cod))
                except ValueError:
                    pass

        cursor.execute("INSERT INTO Vendas (ClienteID, Servico, ValorTotal, ValorPago, DataCompra, FormaPagamento, Observacao) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (cliente_id, servico_desc, valor_total, valor_pago, data_compra, forma_pagto, obs))
        conexao.commit()
        conexao.close()
        flash('Serviço lançado com sucesso e estoque atualizado!', 'success')
        return redirect(url_for('historico_cliente', cliente_id=cliente_id))

    cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()
    cursor.execute("SELECT ID, NomeProduto, Preco, QtdEstoque, UnidadeMedida FROM Produtos")
    produtos = cursor.fetchall()
    conexao.close()
    return render_template_string(LANCAMENTO_SERVICO_HTML, cliente=cliente, produtos=produtos)

@app.route('/cliente/historico/<int:cliente_id>')
def historico_cliente(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()
    cursor.execute("SELECT ID, ClienteID, Servico, ValorTotal, ValorPago, DataCompra, FormaPagamento, Observacao FROM Vendas WHERE ClienteID=?", (cliente_id,))
    vendas = cursor.fetchall()
    conexao.close()
    return render_template_string(HISTORICO_HTML, cliente=cliente, vendas=vendas)

@app.route('/venda/excluir/<int:id>')
def excluir_venda(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT ClienteID FROM Vendas WHERE ID=?", (id,))
    res = cursor.fetchone()
    cliente_id = res[0] if res else None
    cursor.execute("DELETE FROM Vendas WHERE ID=?", (id,))
    conexao.commit()
    conexao.close()
    flash('Lançamento excluído!', 'success')
    if cliente_id:
        return redirect(url_for('historico_cliente', cliente_id=cliente_id))
    return redirect(url_for('clientes'))

@app.route('/cliente/pdf/<int:cliente_id>')
def gerar_pdf_cliente(cliente_id):
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM Clientes WHERE ID=?", (cliente_id,))
    cliente = cursor.fetchone()
    cursor.execute("SELECT ID, Servico, ValorTotal, ValorPago, DataCompra, FormaPagamento FROM Vendas WHERE ClienteID=?", (cliente_id,))
    vendas = cursor.fetchall()
    conexao.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Extrato de Conta - {cliente[1]}")
    p.drawString(100, 730, f"Telefone: {cliente[3] or '-'} | Veículo: {cliente[4] or '-'}")
    
    y = 690
    for v in vendas:
        p.drawString(100, y, f"Data: {v[4]} | Servico: {v[1]} | Total: R$ {v[2]:.2f} | Pago: R$ {v[3]:.2f}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 750

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"extrato_{cliente[1]}.pdf", mimetype='application/pdf')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    conexao = sqlite3.connect(BANCO_DADOS)
    cursor = conexao.cursor()
    cursor.execute("SELECT SUM(ValorPago) FROM Vendas")
    total_receitas = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(Valor) FROM Despesas")
    total_despesas = cursor.fetchone()[0] or 0.0
    conexao.close()
    
    dashboard_html = BASE_LAYOUT.replace("{% block content %}{% endblock %}", f"""
    <div class="space-y-6">
        <h1 class="text-2xl font-bold text-white"><i class="fa-solid fa-chart-line text-cyan-400 mr-2"></i> Dashboard Financeiro</h1>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow">
                <p class="text-slate-400 text-xs font-bold uppercase">Total Receitas</p>
                <p class="text-3xl font-bold text-emerald-400 mt-2">R$ {total_receitas:.2f}</p>
            </div>
            <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow">
                <p class="text-slate-400 text-xs font-bold uppercase">Total Despesas</p>
                <p class="text-3xl font-bold text-red-400 mt-2">R$ {total_despesas:.2f}</p>
            </div>
            <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow">
                <p class="text-slate-400 text-xs font-bold uppercase">Saldo Líquido</p>
                <p class="text-3xl font-bold text-cyan-400 mt-2">R$ {(total_receitas - total_despesas):.2f}</p>
            </div>
        </div>
    </div>
    """)
    return render_template_string(dashboard_html)

if __name__ == '__main__':
    app.run(debug=True)
