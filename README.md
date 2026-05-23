# Bonding — Setup Local

Guia para rodar o projeto completo (backend + frontend) localmente.

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [Node.js 20+](https://nodejs.org/) e npm
- [Python 3.12](https://www.python.org/) (somente se for rodar o backend fora do Docker)
- Clone o repositório do [Frontend](https://github.com/LouisCharlles/soul-match-glide) 

```
git clone https://github.com/LouisCharlles/soul-match-glide
```
---


## 1. Backend (Django)

### 1.1 Variáveis de ambiente

Na raiz de `bonding/`, copie o arquivo de exemplo e preencha os valores:

```bash
cp .env.compose .env
```

Variáveis obrigatórias para rodar localmente:

```env
SECRET_KEY=qualquer-string-longa-e-aleatoria
DEBUG=true
DATABASE_URL=postgres://postgres:postgres@localhost:5432/bonding
REDIS_URL=redis://localhost:6379/1
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FRONTEND_URL=http://localhost:5173
```

Variáveis opcionais (funcionalidades específicas):

```env
# Pagamentos
ABACATEPAY_API_KEY=
ABACATEPAY_WEBHOOK_TOKEN=

# Geolocalização / Sugestão de encontros
GOOGLE_MAPS_API_KEY=

# Verificação de identidade por reconhecimento facial
AWS_REKOGNITION_ENABLED=false
VERIFICATION_PROVIDER=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=

# Spotify
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# Supabase (armazenamento de arquivos)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# LLM (Google Gemini)
GEMINI_API_KEY=

# E-mail
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
```

---

### 1.2 Rodar localmente (ambiente virtual Python)

```bash
cd bonding

# Criar e ativar virtualenv
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Aplicar migrações
python manage.py migrate

# Subir o servidor (ASGI com suporte a WebSocket)
python manage.py runserver
```

> Para WebSockets funcionarem em desenvolvimento, use Daphne em vez do runserver padrão:
> ```bash
> daphne -b 0.0.0.0 -p 8000 setup.asgi:application
> ```

Redis precisa estar rodando localmente. A forma mais simples:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

---

### 1.3 Criar superusuário (opcional)

```bash
python manage.py createsuperuser
```

O painel admin estará em `http://localhost:8000/admin/`.

---


## 2. Frontend (React)

### 2.1 Variáveis de ambiente

Na raiz de `soul-match-glide/`, crie o arquivo `.env`:

```bash
cd ../soul-match-glide
cp .env.example .env    # se não existir, crie manualmente
```

Conteúdo mínimo:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_GOOGLE_MAPS_API_KEY=          # opcional — necessário para sugestão de encontros
```

---

### 2.2 Instalar dependências e rodar

```bash
cd soul-match-glide
npm install
npm run dev
```

O frontend estará disponível em `http://localhost:5173`.

---

## 3. Rodando tudo junto

Em terminais separados:

```bash
# Terminal 1 — Backend
cd bonding && python manage.py runserver

# Terminal 2 — Frontend
cd soul-match-glide && npm run dev
```

- As portas do frontend devem estar apontando pra porta 8000 do backend para consumir a API.
- O CORS_ALLOWED_ORIGINS no seu env tem que incluir o localhost e a porta que aponta pro frontend, nesse caso localhost:8080.
---

## 4. Documentação da API

Com o backend rodando, acesse:

- Swagger UI: `http://localhost:8000/swagger/`
- Redoc: `http://localhost:8000/redoc/`
