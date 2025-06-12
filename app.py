import streamlit as st
import pandas as pd
from datetime import datetime
import io
import plotly.express as px
import os
import json

st.set_page_config(page_title="Cadastro de Quadros de Arte", layout="centered")
st.title("Cadastro de Obras de Arte")

CAMINHO_ARQUIVO = "dados_quadros.json"

# Função para carregar dados do arquivo
def carregar_dados():
    if os.path.exists(CAMINHO_ARQUIVO):
        try:
            return pd.read_json(CAMINHO_ARQUIVO, orient="records").to_dict(orient="records")
        except Exception:
            return []
    return []

# Função para salvar dados no arquivo
def salvar_dados(dados):
    df = pd.DataFrame(dados)
    df.to_json(CAMINHO_ARQUIVO, orient="records", indent=2, force_ascii=False)

# Inicializa os dados
if "dados" not in st.session_state:
    st.session_state.dados = carregar_dados()

if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

with st.expander("📝 Cadastrar Novo Quadro", expanded=True):
    with st.form("formulario_quadro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            id_quadro = st.text_input("ID do Quadro")
            nome_quadro = st.text_input("Nome do Quadro")
            autores = st.text_input("Autor(es)")
        with col2:
            em_carga = st.selectbox("Está em Carga?", ["Sim", "Não"])
            data_entrada = st.date_input("Data de Entrada", format="DD/MM/YYYY") if em_carga == "Sim" else None
            localizacao = st.text_input("Localização Atual")

        descricao = st.text_area("Descrição Resumida")
        submit = st.form_submit_button("Adicionar Quadro")

        if submit:
            entrada_formatada = data_entrada.strftime("%d/%m/%Y") if data_entrada else ""
            st.session_state.dados.append({
                "ID": id_quadro,
                "Nome": nome_quadro,
                "Autor": autores,
                "Em Carga": em_carga,
                "Data de Entrada": entrada_formatada,
                "Localização": localizacao,
                "Descrição": descricao
            })
            salvar_dados(st.session_state.dados)
            st.success("Quadro adicionado com sucesso!")
            st.rerun()

if st.session_state.dados:
    with st.expander("🔍 Visualizar / Editar / Excluir Quadro"):
        df = pd.DataFrame(st.session_state.dados)
        nomes_disponiveis = df["Nome"].tolist()
        quadro_selecionado = st.selectbox("Selecione um quadro:", nomes_disponiveis)

        index = df[df["Nome"] == quadro_selecionado].index[0]
        quadro = st.session_state.dados[index]

        st.markdown(f"**Autor:** {quadro['Autor']}  ")
        st.markdown(f"**Em Carga:** {quadro['Em Carga']}  ")
        st.markdown(f"**Data de Entrada:** {quadro['Data de Entrada']}  ")
        st.markdown(f"**Localização:** {quadro['Localização']}  ")
        st.markdown(f"**Descrição:** {quadro['Descrição']}")

        col1, col2 = st.columns(2)
        if col1.button("✏️ Editar este quadro"):
            st.session_state.editando = index
        if col2.button("🗑️ Excluir este quadro"):
            st.session_state.dados.pop(index)
            salvar_dados(st.session_state.dados)
            st.success("Quadro excluído com sucesso!")
            st.rerun()

        if "editando" in st.session_state:
            st.markdown("---")
            st.markdown("### ✏️ Editar Quadro")
            edit_idx = st.session_state.editando
            item = st.session_state.dados[edit_idx]

            with st.form("editar_form"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome do Quadro", item['Nome'])
                    novo_autor = st.text_input("Autor(es)", item['Autor'])
                with col2:
                    novo_em_carga = st.selectbox("Está em Carga?", ["Sim", "Não"], index=["Sim", "Não"].index(item['Em Carga']))
                    
                    data_entrada_valor = None
                    if item.get('Data de Entrada'):
                        try:
                            data_entrada_valor = datetime.strptime(item['Data de Entrada'], "%d/%m/%Y")
                        except ValueError:
                            data_entrada_valor = None
                    
                    nova_data = st.date_input("Data de Entrada", data_entrada_valor, format="DD/MM/YYYY") if novo_em_carga == "Sim" else None
                    nova_localizacao = st.text_input("Localização Atual", item['Localização'])

                nova_desc = st.text_area("Descrição", item['Descrição'])
                salvar = st.form_submit_button("Salvar Alterações")

                if salvar:
                    nova_entrada_formatada = nova_data.strftime("%d/%m/%Y") if nova_data else ""
                    st.session_state.dados[edit_idx] = {
                        "ID": item['ID'],
                        "Nome": novo_nome,
                        "Autor": novo_autor,
                        "Em Carga": novo_em_carga,
                        "Data de Entrada": nova_entrada_formatada,
                        "Localização": nova_localizacao,
                        "Descrição": nova_desc
                    }
                    salvar_dados(st.session_state.dados)
                    st.success("Quadro atualizado com sucesso!")
                    del st.session_state.editando
                    st.rerun()

    with st.expander("📊 Visualizações Gerais"):
        status_chart = df["Em Carga"].value_counts().reset_index()
        status_chart.columns = ["Status", "Contagem"]
        fig1 = px.pie(status_chart, names='Status', values='Contagem', title='Distribuição por Status de Carga')
        st.plotly_chart(fig1, use_container_width=True)

        autor_chart = df["Autor"].value_counts().reset_index()
        autor_chart.columns = ["Autor", "Quantidade"]
        fig2 = px.bar(autor_chart, x='Autor', y='Quantidade', title='Obras por Autor')
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📥 Exportar Dados"):
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        st.download_button(
            label="📥 Baixar Relatório em Excel",
            data=buffer,
            file_name="relatorio_quadros.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )