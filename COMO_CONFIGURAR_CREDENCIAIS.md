# INSTRUÇÕES: Como Configurar as Credenciais do Google

## Problema Identificado

A chave API fornecida precisa ser configurada, mas o código atual espera uma **Service Account JSON** completa, não apenas uma API key.

## Solução: Duas Opções

### Opção 1: Usar Service Account (Recomendado)

A aplicação está configurada para usar **Google Service Account**, que é mais seguro e apropriado para aplicações server-side.

**Passos:**

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Você já tem uma service account criada (vejo que está na página dela no browser)
3. Clique na service account
4. Vá em **Keys** > **Add Key** > **Create New Key**
5. Escolha **JSON** e baixe o arquivo
6. Abra o arquivo JSON baixado
7. Crie o arquivo `.streamlit/secrets.toml` com o seguinte conteúdo:

```toml
[gcp_service_account]
type = "service_account"
project_id = "COPIE_DO_JSON"
private_key_id = "COPIE_DO_JSON"
private_key = "COPIE_DO_JSON_MANTENHA_OS_\\n"
client_email = "COPIE_DO_JSON"
client_id = "COPIE_DO_JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "COPIE_DO_JSON"
```

8. **IMPORTANTE**: Compartilhe a planilha com o email da service account:
   - Abra a planilha: https://docs.google.com/spreadsheets/d/1_BXjFfmKM_K0ZHpcU8qiEWYQm4weZeekg8E2CbOi_QfE
   - Clique em "Compartilhar"
   - Adicione o email da service account (algo como `nome@projeto.iam.gserviceaccount.com`)
   - Dê permissão de **Editor**

### Opção 2: Usar a API Key Fornecida (Alternativa)

Se você quer usar a API key `fb71a3b307606790241c993560b2b9c86cc9ea5f`, precisaríamos modificar o código para usar autenticação via API key ao invés de service account.

**Isso requer mudanças no código**, pois atualmente ele usa OAuth2 com service account.

## Arquivo a Criar

Crie manualmente o arquivo:

```
g:\Meu Drive\dev\CartoriosBR\.streamlit\secrets.toml
```

Com o conteúdo apropriado (Opção 1 ou 2 acima).

## Verificação

Após criar o arquivo:

1. Reinicie o Streamlit (Ctrl+C e `streamlit run Home.py`)
2. Acesse a página Cadastro CNJ
3. Clique em "Buscar Dados"
4. Verifique se não há mais erros de autenticação

## Nota de Segurança

✅ O arquivo `.streamlit/secrets.toml` está no `.gitignore`
✅ Suas credenciais NÃO serão publicadas no GitHub
✅ Mantenha esse arquivo seguro e não compartilhe

---

## Comando Rápido para Criar o Arquivo

Você pode criar o arquivo via PowerShell:

```powershell
# Navegue até o diretório do projeto
cd "g:\Meu Drive\dev\CartoriosBR"

# Crie o arquivo (substitua CONTEUDO pelo formato acima)
@"
[gcp_service_account]
type = "service_account"
project_id = "SEU_PROJECT_ID"
# ... resto das credenciais
"@ | Out-File -FilePath ".streamlit\secrets.toml" -Encoding UTF8
```

Ou simplesmente crie o arquivo manualmente com o Notepad.
