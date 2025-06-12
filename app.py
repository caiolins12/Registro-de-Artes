import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import json
import streamlit_authenticator as stauth
from pathlib import Path
from PIL import Image
import uuid
import yaml
from yaml.loader import SafeLoader
import re

# --- CONFIGURAÇÃO DA PÁGINA E DIRETÓRIOS ---
st.set_page_config(page_title="Registro de Obras de Arte", layout="wide")

# Diretórios para dados e imagens
PATH_DADOS = Path("user_data")
PATH_DADOS.mkdir(exist_ok=True)
PATH_IMAGENS = Path("user_images")
PATH_IMAGENS.mkdir(exist_ok=True)

# --- ARQUIVO DE CONFIGURAÇÃO (CREDENCIAIS) ---
CONFIG_PATH = Path("config.yaml")

def criar_config_padrao():
    return {
        "cookie": {
            "expiry_days": 30,
            "key": "some_signature_key",
            "name": "some_cookie_name"
        },
        "credentials": {
            "usernames": {}
        }
    }

# Carrega (ou cria) o arquivo de configuração YAML
if not CONFIG_PATH.exists():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(criar_config_padrao(), f, default_flow_style=False, allow_unicode=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.load(f, Loader=SafeLoader)

# Cria admin automaticamente se não existir
if "admin" not in config["credentials"]["usernames"]:
    config["credentials"]["usernames"]["admin"] = {
        "name": "Administrador",
        "email": "admin@admin.com",
        "password": stauth.Hasher.hash("comando")
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

# Cria estrutura de grupos e convites se não existir
if "grupos" not in config:
    config["grupos"] = {}
if "convites" not in config:
    config["convites"] = {}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

# Cria objeto de autenticação usando config
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# Função para garantir que o usuário está autenticado e manter sessão
def garantir_autenticacao():
    auth_status = st.session_state.get('authentication_status')
    if auth_status is not True:
        # Limpa variáveis de sessão relacionadas ao usuário
        for k in ["name", "username", "authentication_status", "dados", "username", "view", "quadro_selecionado_radio", "editing_idx", "add_foto_idx"]:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.auth_view = "Login"
        st.rerun()

# Só força rerun se o usuário tentar acessar área restrita sem estar autenticado
if (
    "authentication_status" in st.session_state
    and st.session_state["authentication_status"] is not True
    and (
        # Só rerun se não está na tela de login/registro
        not ("auth_view" in st.session_state and st.session_state["auth_view"] in ["Login", "Registrar"])
    )
):
    garantir_autenticacao()

st.title("Registro de Obras de Arte")

# --- INTERFACE DE LOGIN / REGISTRO ---
# Só mostra login/registro se não estiver autenticado
name = st.session_state.get('name')
authentication_status = st.session_state.get('authentication_status')
username = st.session_state.get('username')

if not authentication_status:
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "Login"  # ou "Registrar"

    st.session_state.auth_view = st.radio("Acesso", ["Login", "Registrar"], horizontal=True, index=["Login", "Registrar"].index(st.session_state.auth_view))

    if st.session_state.auth_view == "Login":
        authenticator.login('main')
    else:
        with st.form("form_registro"):
            nome = st.text_input("Nome completo")
            email = st.text_input("Email")
            username_new = st.text_input("Nome de usuário (sem espaços)")
            senha = st.text_input("Senha", type="password")
            confirmar = st.text_input("Confirmar Senha", type="password")
            registrar_btn = st.form_submit_button("Registrar")

            if registrar_btn:
                erros = []
                # Formatação (máscaras)
                nome_fmt = nome.strip().title()
                email_fmt = email.strip().lower()
                username_fmt = username_new.strip().lower().replace(" ", "")

                # Validações simples
                if not nome_fmt:
                    erros.append("Nome é obrigatório.")
                if not re.match(r"^[a-z0-9_]{3,20}$", username_fmt):
                    erros.append("Usuário deve ter 3-20 caracteres, somente letras minúsculas, números ou _ .")
                if username_fmt in config["credentials"]["usernames"]:
                    erros.append("Usuário já existe.")
                if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email_fmt):
                    erros.append("Email inválido.")
                # Impede e-mail duplicado
                for u in config["credentials"]["usernames"].values():
                    if u.get("email", "") == email_fmt:
                        erros.append("Já existe uma conta com este e-mail.")
                        break
                if len(senha) < 4:
                    erros.append("Senha deve ter pelo menos 4 caracteres.")
                if senha != confirmar:
                    erros.append("As senhas não coincidem.")

                if erros:
                    for err in erros:
                        st.error(err)
                else:
                    # Hash da senha (API atual)
                    hashed_pw = stauth.Hasher.hash(senha)

                    # Adiciona ao dict de credenciais
                    config["credentials"]["usernames"][username_fmt] = {
                        "name": nome_fmt,
                        "email": email_fmt,
                        "password": hashed_pw
                    }

                    # Salva YAML
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

                    st.success("Usuário registrado com sucesso! Faça login.")
                    st.session_state.auth_view = "Login"
                    st.rerun()

# Recupera informações de autenticação via session_state
name = st.session_state.get('name')
authentication_status = st.session_state.get('authentication_status')
username = st.session_state.get('username')

# --- FUNÇÕES DE DADOS E IMAGENS ---
def get_user_data_path(user_name):
    return PATH_DADOS / f"dados_{user_name}.json"

def carregar_dados(user_name):
    arquivo_dados = get_user_data_path(user_name)
    if arquivo_dados.exists():
        try:
            with open(arquivo_dados, "r", encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []

def salvar_dados(user_name, dados):
    arquivo_dados = get_user_data_path(user_name)
    with open(arquivo_dados, "w", encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def salvar_imagem(imagem_enviada):
    if imagem_enviada:
        try:
            ext = Path(imagem_enviada.name).suffix
            nome_arquivo = f"{uuid.uuid4()}{ext}"
            caminho_imagem = PATH_IMAGENS / nome_arquivo
            
            img = Image.open(imagem_enviada)
            img.save(caminho_imagem)
            return nome_arquivo
        except Exception as e:
            st.error(f"Erro ao salvar imagem: {e}")
            return None
    return None

# --- LÓGICA DA APLICAÇÃO ---
if authentication_status:
    # Painel ADMIN
    if username == "admin":
        st.header("Painel de Administração de Usuários")
        st.write("Abaixo estão todos os usuários cadastrados:")
        usuarios = [
            {"Usuário": u, "Nome": v.get("name", ""), "Email": v.get("email", "")}
            for u, v in config["credentials"]["usernames"].items()
        ]
        df_usuarios = pd.DataFrame(usuarios)
        st.dataframe(df_usuarios, hide_index=True)

        st.subheader("Excluir usuário")
        usuarios_excl = [u for u in config["credentials"]["usernames"] if u != "admin"]
        usuario_del = st.selectbox("Selecione o usuário para deletar:", usuarios_excl)
        if st.button("Deletar usuário"):
            # Remove do config
            del config["credentials"]["usernames"][usuario_del]
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            st.success(f"Usuário '{usuario_del}' removido com sucesso!")
            st.rerun()

        st.divider()
        authenticator.logout('Logout', 'main')
    else:
        # Carrega os dados do usuário logado
        if "dados" not in st.session_state or st.session_state.get("username") != username:
            st.session_state.dados = carregar_dados(username)
            st.session_state.username = username

        # --- BARRA LATERAL (SIDEBAR) ---
        with st.sidebar:
            st.markdown(f"<h3 style='margin-bottom:0'>Bem-vindo, <span style='color:#4F8BF9'>{name}</span>!</h3>", unsafe_allow_html=True)
            authenticator.logout('Logout', 'sidebar')
            st.divider()

            st.header("👥 Grupos de Usuários")
            meus_grupos = [g for g, membros in config["grupos"].items() if username in membros]
            todos_grupos = list(config["grupos"].keys())

            # --- Convites pendentes ---
            convites_recebidos = [g for g, lst in config["convites"].items() if username in lst]
            if convites_recebidos:
                st.markdown(f"<b>Convites pendentes:</b>", unsafe_allow_html=True)
                for grupo in convites_recebidos:
                    colc1, colc2 = st.columns([2,1])
                    with colc1:
                        st.info(f"Você foi convidado para o grupo '{grupo}'")
                    with colc2:
                        if st.button("Aceitar", key=f"aceitar_{grupo}"):
                            config["convites"][grupo].remove(username)
                            if grupo not in config["grupos"]:
                                config["grupos"][grupo] = []
                            config["grupos"][grupo].append(username)
                            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                            st.success(f"Você agora faz parte do grupo '{grupo}'!")
                            st.rerun()
                        if st.button("Recusar", key=f"recusar_{grupo}"):
                            config["convites"][grupo].remove(username)
                            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                            st.info(f"Convite recusado.")
                            st.rerun()
                st.divider()

            aba_grupos = st.tabs(["Meus Grupos", "Criar Grupo", "Convidar Membro"])

            # --- Meus Grupos ---
            with aba_grupos[0]:
                if meus_grupos:
                    grupo_sel_sidebar = st.selectbox("Selecione um grupo para ver membros:", meus_grupos, key="grupo_sidebar_sel")
                    membros = config["grupos"][grupo_sel_sidebar]
                    membros_info = [
                        {
                            "Usuário": u,
                            "Nome": config["credentials"]["usernames"].get(u, {}).get("name", "")
                        } for u in membros
                    ]
                    st.markdown(f"<b>Membros do grupo <span style='color:#4F8BF9'>{grupo_sel_sidebar}</span>:</b>", unsafe_allow_html=True)
                    st.dataframe(membros_info, hide_index=True, use_container_width=True)
                    # Sair do grupo
                    if st.button(f"Sair do grupo '{grupo_sel_sidebar}'", key="btn_sair_grupo_modern"):
                        if username in config["grupos"][grupo_sel_sidebar]:
                            config["grupos"][grupo_sel_sidebar].remove(username)
                            if not config["grupos"][grupo_sel_sidebar]:
                                del config["grupos"][grupo_sel_sidebar]
                            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                            st.success(f"Você saiu do grupo '{grupo_sel_sidebar}'!")
                            st.rerun()
                else:
                    st.info("Você não participa de nenhum grupo.")

            # --- Criar Grupo ---
            with aba_grupos[1]:
                nome_grupo = st.text_input("Nome do grupo", key="novo_grupo_modern")
                if st.button("Criar grupo", key="btn_criar_grupo_modern"):
                    nome_grupo_fmt = nome_grupo.strip().lower().replace(" ", "_")
                    if not nome_grupo_fmt:
                        st.warning("Digite um nome para o grupo.")
                    elif nome_grupo_fmt in config["grupos"] or nome_grupo_fmt in config["convites"]:
                        st.warning("Já existe um grupo com esse nome.")
                    else:
                        config["grupos"][nome_grupo_fmt] = [username]
                        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                        st.success(f"Grupo '{nome_grupo_fmt}' criado e você foi adicionado!")
                        st.rerun()

            # --- Convidar Membro ---
            with aba_grupos[2]:
                if meus_grupos:
                    grupo_convidar = st.selectbox("Escolha o grupo para convidar:", meus_grupos, key="grupo_convidar")
                    usuario_convidar = st.text_input("Usuário para convidar", key="usuario_convidar")
                    if st.button("Convidar usuário", key="btn_convidar_usuario"):
                        usuario_convidar_fmt = usuario_convidar.strip().lower().replace(" ", "")
                        if not usuario_convidar_fmt:
                            st.warning("Digite o nome de usuário.")
                        elif usuario_convidar_fmt not in config["credentials"]["usernames"]:
                            st.warning("Usuário não encontrado.")
                        elif usuario_convidar_fmt in config["grupos"][grupo_convidar]:
                            st.info("Usuário já faz parte do grupo.")
                        elif grupo_convidar in config["convites"] and usuario_convidar_fmt in config["convites"][grupo_convidar]:
                            st.info("Usuário já foi convidado para este grupo.")
                        else:
                            if grupo_convidar not in config["convites"]:
                                config["convites"][grupo_convidar] = []
                            config["convites"][grupo_convidar].append(usuario_convidar_fmt)
                            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                            st.success(f"Convite enviado para '{usuario_convidar_fmt}'!")
                            st.rerun()
                else:
                    st.info("Crie ou entre em um grupo para poder convidar membros.")

            st.divider()
            # Seleção de acervo: pessoal ou de grupo
            opcoes_acervo = ["Meu Acervo"] + meus_grupos
            acervo_sel = st.selectbox("Visualizar acervo de:", opcoes_acervo, key="acervo_sel")

            # Carrega quadros do acervo selecionado
            if acervo_sel == "Meu Acervo":
                quadros_exibir = st.session_state.dados
            else:
                # Junta quadros de todos os membros do grupo
                membros = config["grupos"].get(acervo_sel, [])
                quadros_exibir = []
                for membro in membros:
                    dados_membro = carregar_dados(membro)
                    for q in dados_membro:
                        q_copia = q.copy()
                        q_copia["__dono__"] = membro
                        quadros_exibir.append(q_copia)

            # Cria uma lista de nomes de quadros para o menu
            nomes_quadros = [q.get("Nome", "Sem Nome") + (f" (de {q['__dono__']})" if "__dono__" in q else "") for q in quadros_exibir]

            # Menu para selecionar, editar ou excluir um quadro
            quadro_selecionado_nome = st.radio(
                "Selecione um quadro para ver os detalhes:",
                nomes_quadros,
                index=None,
                key="quadro_selecionado_radio"
            )

            st.divider()
            # Botão para adicionar um novo quadro (só se for acervo pessoal)
            if acervo_sel == "Meu Acervo" and st.button("🖼️ Adicionar Novo Quadro"):
                st.session_state.view = "add_new"
                st.rerun()

        # --- ÁREA PRINCIPAL ---
        # Mostra qual acervo está sendo exibido
        if 'acervo_sel' in st.session_state:
            if st.session_state['acervo_sel'] == 'Meu Acervo':
                st.subheader("Visualizando: Meu Acervo")
            else:
                st.subheader(f"Visualizando acervo do grupo: {st.session_state['acervo_sel']}")

        # Visualização para Adicionar Novo Quadro
        if st.session_state.get("view") == "add_new":
            st.header("📝 Cadastrar Novo Quadro")
            with st.form("formulario_quadro", clear_on_submit=True):
                imagem_enviada = st.file_uploader("Foto do Quadro (miniatura)", type=["png", "jpg", "jpeg"])
                nome_quadro = st.text_input("Nome do Quadro", key="add_nome")
                autores = st.text_input("Autor(es)", key="add_autor")
                localizacao = st.text_input("Localização Atual", key="add_loc")
                data_entrada = st.date_input("Data de Entrada", format="DD/MM/YYYY", key="add_data")
                descricao = st.text_area("Descrição Resumida", key="add_desc")
                
                submit = st.form_submit_button("Adicionar Quadro")
                if submit:
                    if nome_quadro and autores:
                        caminho_imagem = salvar_imagem(imagem_enviada)
                        
                        novo_quadro = {
                            "ID": str(uuid.uuid4()),
                            "Nome": nome_quadro,
                            "Autor": autores,
                            "Data de Entrada": data_entrada.strftime("%d/%m/%Y") if data_entrada else "",
                            "Localização": localizacao,
                            "Descrição": descricao,
                            "CaminhoImagem": caminho_imagem
                        }
                        st.session_state.dados.append(novo_quadro)
                        salvar_dados(username, st.session_state.dados)
                        st.success("Quadro adicionado com sucesso!")
                        st.session_state.view = None
                        st.rerun()
                    else:
                        st.warning("Nome do quadro e Autor são campos obrigatórios.")

        # Visualização de Detalhes, Edição e Exclusão
        elif quadro_selecionado_nome:
            # Encontra o quadro selecionado nos dados exibidos
            index_selecionado = nomes_quadros.index(quadro_selecionado_nome)
            quadro = quadros_exibir[index_selecionado]

            st.header(f"Detalhes de: *{quadro.get('Nome')}*")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if quadro.get("CaminhoImagem") and (PATH_IMAGENS / quadro["CaminhoImagem"]).exists():
                    st.image(str(PATH_IMAGENS / quadro["CaminhoImagem"]), use_column_width=True)
                else:
                    st.info("Nenhuma imagem disponível para este quadro.")
                # Botão para adicionar/alterar foto depois do cadastro (só se for dono do quadro)
                pode_editar_foto = (acervo_sel == "Meu Acervo") or ("__dono__" in quadro and quadro["__dono__"] == username)
                if pode_editar_foto and st.button("Adicionar/Alterar Foto deste Quadro"):
                    st.session_state.add_foto_idx = index_selecionado
                    st.rerun()
                # Formulário para upload de foto pós-cadastro
                if pode_editar_foto and st.session_state.get("add_foto_idx") == index_selecionado:
                    with st.form("form_foto_quadro"): 
                        nova_foto = st.file_uploader("Escolha a nova foto", type=["png", "jpg", "jpeg"])
                        salvar_foto = st.form_submit_button("Salvar Foto")
                        if salvar_foto and nova_foto:
                            caminho_img = salvar_imagem(nova_foto)
                            # Atualiza a foto no acervo correto
                            if acervo_sel == "Meu Acervo" or ("__dono__" in quadro and quadro["__dono__"] == username):
                                if acervo_sel == "Meu Acervo":
                                    st.session_state.dados[index_selecionado]["CaminhoImagem"] = caminho_img
                                    salvar_dados(username, st.session_state.dados)
                                else:
                                    # Atualiza no arquivo do dono
                                    dados_dono = carregar_dados(quadro["__dono__"])
                                    for q in dados_dono:
                                        if q["ID"] == quadro["ID"]:
                                            q["CaminhoImagem"] = caminho_img
                                            break
                                    salvar_dados(quadro["__dono__"], dados_dono)
                            st.success("Foto atualizada!")
                            del st.session_state.add_foto_idx
                            st.rerun()
                        elif salvar_foto:
                            st.warning("Selecione uma imagem.")
            
            with col2:
                st.markdown(f"**Autor:** {quadro.get('Autor', 'N/A')}")
                st.markdown(f"**Data de Entrada:** {quadro.get('Data de Entrada', 'N/A')}")
                st.markdown(f"**Localização:** {quadro.get('Localização', 'N/A')}")
                st.markdown(f"**Descrição:**")
                st.markdown(quadro.get('Descrição', 'N/A'))
                
                btn1, btn2 = st.columns(2)
                pode_editar = (acervo_sel == "Meu Acervo") or ("__dono__" in quadro and quadro["__dono__"] == username)
                if pode_editar and btn1.button("✏️ Editar", use_container_width=True):
                    st.session_state.editing_idx = index_selecionado
                    st.rerun()
                if pode_editar and btn2.button("🗑️ Excluir", use_container_width=True):
                    # Opcional: deletar imagem do disco
                    if quadro.get("CaminhoImagem"):
                        Path(PATH_IMAGENS / quadro["CaminhoImagem"]).unlink(missing_ok=True)
                    # Remove do acervo correto
                    if acervo_sel == "Meu Acervo":
                        st.session_state.dados.pop(index_selecionado)
                        salvar_dados(username, st.session_state.dados)
                    else:
                        dados_dono = carregar_dados(quadro["__dono__"])
                        dados_dono = [q for q in dados_dono if q["ID"] != quadro["ID"]]
                        salvar_dados(quadro["__dono__"], dados_dono)
                    st.success("Quadro excluído com sucesso!")
                    st.rerun()

            if "editing_idx" in st.session_state and st.session_state.editing_idx == index_selecionado and pode_editar:
                st.divider()
                st.header("✏️ Editando Quadro")
                with st.form("editar_form"):
                    # Carrega o dado correto para edição
                    if acervo_sel == "Meu Acervo":
                        item_para_editar = st.session_state.dados[st.session_state.editing_idx]
                    else:
                        item_para_editar = quadro
                    novo_nome = st.text_input("Nome do Quadro", value=item_para_editar.get('Nome', ''))
                    novo_autor = st.text_input("Autor(es)", value=item_para_editar.get('Autor', ''))
                    nova_localizacao = st.text_input("Localização", value=item_para_editar.get('Localização', ''))
                    data_valor = None
                    if item_para_editar.get("Data de Entrada"):
                        try:
                            data_valor = datetime.strptime(item_para_editar["Data de Entrada"], "%d/%m/%Y")
                        except ValueError:
                            pass
                    nova_data = st.date_input("Data de Entrada", value=data_valor, format="DD/MM/YYYY")
                    nova_desc = st.text_area("Descrição", value=item_para_editar.get('Descrição', ''))
                    nova_imagem = st.file_uploader("Trocar Foto", type=["png", "jpg", "jpeg"])
                    salvar_edicao = st.form_submit_button("Salvar Alterações")
                    if salvar_edicao:
                        caminho_imagem_editada = item_para_editar.get("CaminhoImagem")
                        if nova_imagem:
                            # Deleta a imagem antiga se existir
                            if caminho_imagem_editada:
                                (PATH_IMAGENS / caminho_imagem_editada).unlink(missing_ok=True)
                            # Salva a nova imagem
                            caminho_imagem_editada = salvar_imagem(nova_imagem)
                        # Atualiza os dados
                        if acervo_sel == "Meu Acervo":
                            st.session_state.dados[st.session_state.editing_idx] = {
                                "ID": item_para_editar["ID"],
                                "Nome": novo_nome,
                                "Autor": novo_autor,
                                "Data de Entrada": nova_data.strftime("%d/%m/%Y") if nova_data else "",
                                "Localização": nova_localizacao,
                                "Descrição": nova_desc,
                                "CaminhoImagem": caminho_imagem_editada
                            }
                            salvar_dados(username, st.session_state.dados)
                        else:
                            dados_dono = carregar_dados(quadro["__dono__"])
                            for idx, q in enumerate(dados_dono):
                                if q["ID"] == item_para_editar["ID"]:
                                    dados_dono[idx] = {
                                        "ID": item_para_editar["ID"],
                                        "Nome": novo_nome,
                                        "Autor": novo_autor,
                                        "Data de Entrada": nova_data.strftime("%d/%m/%Y") if nova_data else "",
                                        "Localização": nova_localizacao,
                                        "Descrição": nova_desc,
                                        "CaminhoImagem": caminho_imagem_editada
                                    }
                                    break
                            salvar_dados(quadro["__dono__"], dados_dono)
                        st.success("Quadro atualizado com sucesso!")
                        del st.session_state.editing_idx
                        st.rerun()
        else:
            st.info("Selecione um quadro na barra lateral para ver os detalhes ou adicione um novo quadro.")

elif authentication_status is False:
    st.error('Usuário/senha incorreto')
elif authentication_status is None:
    st.warning('Por favor, digite seu usuário e senha')

# --- REMOVER ARQUIVOS ANTIGOS E NÃO UTILIZADOS ---
# Opcional: Lógica para limpar arquivos antigos se necessário.
# Por exemplo, o dados_quadros.json não é mais usado da mesma forma.
# if os.path.exists("dados_quadros.json"):
#     os.remove("dados_quadros.json")