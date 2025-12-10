# Guia: Como Configurar a Nova Chave da API do Google

## Localização do Arquivo de Credenciais

As credenciais da API do Google devem ser configuradas no arquivo:

```
g:\Meu Drive\dev\CartoriosBR\.streamlit\secrets.toml
```

## Formato do Arquivo

O arquivo `secrets.toml` deve ter o seguinte formato:

```toml
# Credenciais da Service Account do Google Cloud
[gcp_service_account]
type = "service_account"
project_id = "seu-projeto-id"
private_key_id = "sua-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nSUA_CHAVE_PRIVADA_AQUI\n-----END PRIVATE KEY-----\n"
client_email = "sua-service-account@seu-projeto.iam.gserviceaccount.com"
client_id = "seu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/sua-service-account%40seu-projeto.iam.gserviceaccount.com"

# ID da Planilha Google Sheets (opcional, já está hardcoded no código)
SHEET_ID = "1SkxwQoAnNpcNBg1niLpaRaMs79h8rp143NPgsr1EAXo"

# Credenciais Supabase (se usar)
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_KEY = "sua-chave-supabase"
```

## Como Obter as Credenciais

### Opção 1: Arquivo JSON da Service Account

Se você tem um arquivo JSON da service account (geralmente baixado do Google Cloud Console):

1. Abra o arquivo JSON
2. Copie todo o conteúdo
3. Cole no `secrets.toml` seguindo o formato acima

**Exemplo de conversão JSON → TOML:**

Se seu JSON é assim:
```json
{
  "type": "service_account",
  "project_id": "meu-projeto",
  "private_key": "-----BEGIN PRIVATE KEY-----\nABC123...\n-----END PRIVATE KEY-----\n",
  ...
}
```

No `secrets.toml` fica:
```toml
[gcp_service_account]
type = "service_account"
project_id = "meu-projeto"
private_key = "-----BEGIN PRIVATE KEY-----\nABC123...\n-----END PRIVATE KEY-----\n"
...
```

### Opção 2: Criar Service Account no Google Cloud

Se você ainda não tem uma service account:

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Vá em **IAM & Admin** > **Service Accounts**
3. Clique em **Create Service Account**
4. Dê um nome (ex: "streamlit-app")
5. Clique em **Create and Continue**
6. Adicione as roles:
   - **Editor** (para Google Sheets)
   - Ou mais específico: **Google Sheets API** com permissão de edição
7. Clique em **Done**
8. Clique na service account criada
9. Vá em **Keys** > **Add Key** > **Create New Key**
10. Escolha **JSON** e baixe o arquivo
11. Use o conteúdo desse arquivo no `secrets.toml`

## Permissões Necessárias

A service account precisa ter acesso às planilhas do Google Sheets:

1. Abra a planilha no Google Sheets
2. Clique em **Compartilhar**
3. Adicione o email da service account (ex: `streamlit-app@meu-projeto.iam.gserviceaccount.com`)
4. Dê permissão de **Editor**

## Verificação

Após configurar, reinicie o Streamlit:

1. Pare o servidor (Ctrl+C no terminal)
2. Inicie novamente: `streamlit run Home.py`
3. Teste a página Cadastro CNJ ou Receita TJRJ

## Troubleshooting

### Erro: "Credentials not found"
- Verifique se o arquivo `.streamlit/secrets.toml` existe
- Verifique se está no formato correto (TOML, não JSON)

### Erro: "Permission denied"
- Verifique se a service account foi adicionada como editor na planilha
- Verifique se o email está correto

### Erro: "Invalid private key"
- Certifique-se de que a `private_key` está entre aspas duplas
- Mantenha os `\n` na chave (não substitua por quebras de linha reais)

## Exemplo Completo

Aqui está um exemplo completo (com dados fictícios):

```toml
[gcp_service_account]
type = "service_account"
project_id = "cartoriosbr-123456"
private_key_id = "abc123def456"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n"
client_email = "streamlit-app@cartoriosbr-123456.iam.gserviceaccount.com"
client_id = "123456789012345678901"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/streamlit-app%40cartoriosbr-123456.iam.gserviceaccount.com"
```

---

**IMPORTANTE**: O arquivo `secrets.toml` já está no `.gitignore`, então suas credenciais não serão commitadas no Git. Mantenha esse arquivo seguro!
