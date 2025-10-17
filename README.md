# NFSe Headless API

Serviço em **Python 3.11.8 + FastAPI** que emite Notas Fiscais de Serviço (NFSe) via *web‑scraping headless* (Playwright) no portal **NFSe Nacional** e grava todas as informações no **em um banco de dados**.

**Python 3.12 ou superior não é compatível, pois o Playwright ainda não foi atualizado para suportar essa versão.**

*Necessario instalar Python 3.11 no site oficial*
---

## ✨ Principais Recursos

| Módulo               | Descrição                                                              |
| -------------------- | ---------------------------------------------------------------------- |
| **FastAPI**          | Endpoints REST (`/api/emitir-nfse`, `/api/nfse/:uuid`, logs, listagem) |
| **Playwright Async** | Chromium headless; timeout e download de XML/PDF                       |
| **MySQL**            | Tabelas `invoices`, `logs` compartilhadas com projeto PHP              |
| **BackgroundTasks**  | A emissão roda em segundo plano; retorna imediatamente ao front‑end    |

---

## 🖥️ Pré‑requisitos

| Requisito  | Versão mínima                                                |  
| ---------- | ---------------------------------------------------------    |
| Python     | **3.11.8** (Windows exige `WindowsSelectorEventLoopPolicy`)  |
| Playwright | 1.53 (instala browsers via `playwright install`)             |

---

## 🚀 Instalação Rápida

```bash
# 1. entre na pasta
$ cd BotAPI

# 2. crie e ative o venv
$ python -3.11 -m venv venv
$ venv\Scripts\Activate

# 3. instale dependências
(venv)$ pip install -r requirements.txt

# 4. instale os navegadores do Playwright
(venv)$ playwright install

# 5. cd na pasta do aplicativo
(venv)$ cd nfse_fastapi

# 6. comando para rodar uvicorn
(venv)$ uvicorn main:app --reload
```

---

Acesse `http://localhost:8000/docs` (Swagger) depois de rodar o servidor.

---

## 📡 Endpoints Essenciais

| Método   | Rota                                | Descrição                               |
| -------- | ----------------------------------- | --------------------------------------- |
| **POST** | `/api/emitir-nfse`                  | Endpoint principal para emissão de NFSe |
| **GET**  | `/api/nfse/{uuid}`                  | Consulta nota pelo UUID                 |
| **GET**  | `/api/nfse/{uuid}/logs`             | Logs de status da nota                  |
| **GET**  | `/api/nfses?limit=50&offset=0`      | Lista notas paginadas                   |

### Exemplo `curl`

```bash
    {
    "cnpj_emissor": "string",
    "senha_emissor": "string",
    "data_emissao": "string", # DD/MM/AAAA
    "cnpj_cliente": "string",
    "telefone_cliente": "string",
    "email_cliente": "string",
    "valor": 0,
    "cnae_code": "string",
    "cnae_service": "string",
    "city": "string", # CIDADE/ESTADO
    "descricao_servico": "string"
    }
```

A resposta devolve `message` + `uuid` + `status=PROCESSING`. Use esse `uuid` para consultar.

---



