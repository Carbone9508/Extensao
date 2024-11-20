from flask import Flask, render_template, request, jsonify
import os
import requests
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
from bs4 import BeautifulSoup

app = Flask(__name__)

# URL base do site
BASE_URL = "https://energi.eletrica.ufpr.br/static/arquivos/"

# Pasta para salvar gráficos interativos
GRAPH_FOLDER = os.path.join(os.getcwd(), "static")  # Caminho absoluto para a pasta
os.makedirs(GRAPH_FOLDER, exist_ok=True)


def get_csv_files(base_url, path=""):
    """Obtém a lista de arquivos CSV do site e subpastas."""
    response = requests.get(f"{base_url}{path}")
    if response.status_code != 200:
        return [], []

    soup = BeautifulSoup(response.text, "html.parser")
    
    files = []
    folders = []

    # Procura por links de arquivos CSV e subpastas
    for link in soup.find_all("a"):
        href = link.get("href")
        if href:
            if href.endswith(".csv"):
                files.append({"name": href, "url": f"{base_url}{path}{href}"})
            elif href.endswith("/"):  # Identifica subpastas
                folders.append({"name": href, "url": f"{base_url}{path}{href}"})

    return files, folders


@app.route("/")
def index():
    """Página inicial."""
    return render_template("index.html")


@app.route("/list-files", methods=["GET"])
def list_files():
    """Lista os arquivos CSV e subpastas disponíveis no site."""
    try:
        path = request.args.get("path", "")  # Pega o caminho da subpasta
        files, folders = get_csv_files(BASE_URL, path)

        return jsonify({
            "files": files,
            "folders": folders,
            "path": path
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate-graph", methods=["POST"])
def generate_graph():
    """Gera um gráfico interativo com base no arquivo CSV escolhido."""
    data = request.json
    file_url = data.get("url")
    graph_type = data.get("graphType", "2D")  # Padrão é gráfico 2D

    if not file_url:
        return jsonify({"error": "URL não fornecida"}), 400

    try:
        # Baixar o arquivo CSV
        response = requests.get(file_url)
        if response.status_code != 200:
            return jsonify({"error": "Erro ao baixar o arquivo"}), 400

        # Ler o CSV como DataFrame
        csv_data = response.content.decode("utf-8")
        df = pd.read_csv(io.StringIO(csv_data))

        # Verifica se há pelo menos 2 colunas para gerar o gráfico
        if df.shape[1] < 2:
            return jsonify({"error": "O arquivo CSV deve ter pelo menos 2 colunas para gerar o gráfico."}), 400

        # Geração do gráfico com Plotly
        if graph_type == "3D":
            # Gráfico 3D (x: primeira coluna, y: segunda coluna, z: terceira coluna se existir)
            if df.shape[1] < 3:
                return jsonify({"error": "O gráfico 3D requer pelo menos 3 colunas no arquivo CSV."}), 400
            fig = px.scatter_3d(df, x=df.columns[0], y=df.columns[1], z=df.columns[2], title="Gráfico 3D")
        else:
            # Gráfico 2D padrão
            fig = px.line(df, x=df.columns[0], y=df.columns[1], title="Gráfico 2D")

        # Salvar o gráfico como HTML interativo
        graph_path = os.path.join(GRAPH_FOLDER, "graph.html")
        pio.write_html(fig, file=graph_path, auto_open=False)

        return jsonify({"graphUrl": f"/static/graph.html"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Só ativa o modo de debug se estiver localmente
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=5000)
