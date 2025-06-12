# Registro de Obras de Arte - Aplicação Streamlit

Esta é uma aplicação web simples criada com Streamlit para cadastrar, visualizar, editar e excluir registros de obras de arte.

## Funcionalidades

-   **Cadastro de Obras**: Formulário para adicionar novas obras, incluindo ID, nome, autor, status, data de entrada e localização.
-   **Visualização e Gerenciamento**: Visualize os detalhes de cada obra, edite suas informações ou exclua registros.
-   **Dashboards**: Gráficos interativos que mostram a distribuição de obras por status e por autor.
-   **Exportação**: Baixe todos os dados em um arquivo Excel.

## Como Colocar a Aplicação no Ar

Para que você possa incorporar esta aplicação em seu site HTML, primeiro é necessário implantá-la em um serviço de hospedagem. A forma mais simples e gratuita para aplicações Streamlit é a **Streamlit Community Cloud**.

Siga os passos abaixo:

### Passo 1: Tenha o projeto no GitHub

A Streamlit Community Cloud funciona importando projetos diretamente de um repositório do GitHub.

1.  **Crie uma conta no GitHub**: Se você ainda não tem uma, crie em [github.com](https://github.com).
2.  **Crie um novo repositório**: Crie um repositório público.
3.  **Envie os arquivos do projeto**: Envie os seguintes arquivos para o seu repositório:
    -   `app.py`
    -   `requirements.txt`
    -   `dados_quadros.json` (opcional, se quiser começar com dados existentes)
    -   `README.md` (este arquivo)

### Passo 2: Implantação na Streamlit Community Cloud

1.  **Acesse a Streamlit Community Cloud**: Vá para [share.streamlit.io](https://share.streamlit.io) e faça login com sua conta do GitHub.
2.  **Clique em "New app"**: Você será direcionado para uma página para configurar a implantação.
3.  **Selecione o repositório**: Escolha o repositório que você acabou de criar.
4.  **Verifique as configurações**:
    -   **Repository**: `seu-usuario/seu-repositorio`
    -   **Branch**: `main` (ou a branch principal do seu repositório)
    -   **Main file path**: `app.py`
5.  **Clique em "Deploy!"**: O Streamlit irá construir e implantar sua aplicação. Após alguns instantes, você terá uma URL pública para sua aplicação (algo como `https://seu-app.streamlit.app`).

### Passo 3: Incorporar em seu Site HTML

Com a URL da sua aplicação em mãos, você pode incorporá-la em qualquer página HTML usando um `<iframe>`.

Copie o código do arquivo `index.html` (que também está neste projeto) e cole no seu site. **Lembre-se de substituir `"SUA_URL_DO_STREAMLIT_AQUI"` pela URL real da sua aplicação.**

```html
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minha Galeria de Arte</title>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }
        iframe {
            border: none;
            width: 100%;
            height: 100%;
        }
    </style>
</head>
<body>
    <iframe
        src="SUA_URL_DO_STREAMLIT_AQUI?embed=true"
        width="100%"
        height="100%"
        style="border:none;">
    </iframe>
</body>
</html>
```

O parâmetro `?embed=true` na URL ajuda a otimizar a aparência da aplicação para incorporação, removendo o cabeçalho e o menu do Streamlit. 