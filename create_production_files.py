#!/usr/bin/env python3
"""
Cria arquivos de produção diretamente
"""

from pathlib import Path

def create_deployment_guide():
    """Cria guia de deployment"""
    guide = """# 🚀 FORCE ONE IT LEAD EXTRACTOR - DEPLOYMENT GUIDE

## 📋 Status Atual do Sistema

✅ **FUNCIONALIDADES IMPLEMENTADAS:**
- Sistema de scoring AWS
- Extração Google Maps
- Enriquecimento CNPJ
- Análise tecnográficas  
- Integração HubSpot
- Compliance LGPD
- API REST completa
- Prospect Playlists IA
- Job change monitoring

## 🛠️ Instalação Rápida

### 1. Clone e Setup
```bash
git clone https://github.com/fernandodgl/forceoneit-lead-extractor.git
cd forceoneit-lead-extractor
python -m pip install -r requirements.txt
```

### 2. Configuração
```bash
# Copiar .env
cp .env.example .env

# Editar com suas API keys
# GOOGLE_MAPS_API_KEY=sua_key_aqui
# HUBSPOT_API_KEY=sua_key_aqui (opcional)
```

### 3. Teste
```bash
python test_system.py
python status_check.py
```

## 🔧 APIs Necessárias

### Google Maps API (Obrigatória)
1. Console: https://console.cloud.google.com/
2. Enable: Places API, Geocoding API
3. Create API Key
4. Remove IP restrictions (ou configure seu IP)
5. Teste: python test_google_maps.py

### HubSpot (Recomendada)
1. App: https://app.hubspot.com/
2. Settings > Integrations > Private Apps
3. Create app com scopes:
   - crm.objects.companies.read/write
   - crm.objects.contacts.read/write
   - crm.objects.deals.read/write
4. Copy access token
5. Teste: python setup_hubspot.py

## 🚀 Como Usar

### Comandos Básicos
```bash
# Pipeline completo
python leadextractor.py pipeline --sector banking --limit 20

# Extração simples
python leadextractor.py extract --sector technology --limit 10

# Enriquecimento
python leadextractor.py enrich leads.json

# Scoring
python leadextractor.py score enriched_leads.json --format excel

# Sync HubSpot
python leadextractor.py sync-hubspot scored_leads.json
```

### API REST
```bash
# Iniciar servidor
python leadextractor.py start-api --port 5000

# Endpoints disponíveis:
# GET  /health
# POST /api/v1/extract/companies
# POST /api/v1/pipeline/complete
# POST /api/v1/hubspot/sync
```

## 📊 Monitoramento

### Status Check
```bash
python status_check.py
```

### Outputs Típicos
- **CPU/Memória**: Monitoramento de recursos
- **APIs**: Status de configuração
- **Arquivos**: Contagem de exports/cache/logs

## 🛡️ Segurança e Compliance

### LGPD
- ✅ Bases legais configuradas
- ✅ Consentimentos registrados
- ✅ Direitos dos titulares
- ✅ Audit trail completo

### Rate Limiting
- Google Maps: 30 req/min
- HubSpot: Automático
- LinkedIn: Manual (cuidado)

## 🎯 Próximos Passos

1. **Configure Google Maps API**
   - Remova restrições IP temporariamente
   - Teste extração completa

2. **Configure HubSpot** (opcional)
   - Para sync automático com CRM
   - Criação de deals qualificados

3. **Uso em Produção**
   - Defina processos de backup
   - Configure monitoramento
   - Estabeleça rotinas de manutenção

## 🆘 Troubleshooting

### Google Maps REQUEST_DENIED
```bash
# Teste a API
python test_google_maps.py

# Soluções:
# 1. Remover IP restrictions
# 2. Verificar billing account
# 3. Confirmar APIs habilitadas
```

### Problemas de Encoding
- Sistema testado no Windows
- Usa UTF-8 para arquivos
- Evita emojis em outputs CLI

### Performance
- Limite batch sizes para memória
- Use cache para requests repetidos
- Configure timeouts adequados

## 📞 Suporte

- GitHub: https://github.com/fernandodgl/forceoneit-lead-extractor
- Issues: Para bugs e melhorias
- Documentação: README.md completo
"""
    
    with open('DEPLOYMENT.md', 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print("Criado: DEPLOYMENT.md")

def create_docker_files():
    """Cria arquivos Docker"""
    
    # Dockerfile
    dockerfile = """FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \\
    wget curl gnupg unzip \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p data/cache data/exports logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Run API
CMD ["python", "leadextractor.py", "start-api", "--host", "0.0.0.0", "--port", "5000"]
"""
    
    # docker-compose.yml
    compose = """version: '3.8'

services:
  leadextractor:
    build: .
    ports:
      - "5000:5000"
    environment:
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
      - HUBSPOT_API_KEY=${HUBSPOT_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""
    
    # .dockerignore
    dockerignore = """__pycache__/
*.pyc
*.pyo
.pytest_cache/
.git/
.env
*.log
.DS_Store
.vscode/
"""
    
    files = [
        ('Dockerfile', dockerfile),
        ('docker-compose.yml', compose),
        ('.dockerignore', dockerignore)
    ]
    
    for filename, content in files:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Criado: {filename}")

def create_quick_start():
    """Cria script de início rápido"""
    script = """#!/usr/bin/env python3
\"\"\"
Quick Start - Force One IT Lead Extractor
\"\"\"

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    print(f"Executando: {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True)
        print(f"{description} - OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{description} - ERRO: {e}")
        return False

def quick_start():
    print("=== FORCE ONE IT LEAD EXTRACTOR - QUICK START ===")
    print()
    
    # Check Python
    print(f"Python version: {sys.version}")
    
    # Check if dependencies are installed
    try:
        import pandas, requests, click
        print("✅ Dependências instaladas")
    except ImportError:
        print("❌ Instalando dependências...")
        if not run_command("python -m pip install -r requirements.txt", "Install dependencies"):
            return False
    
    # Check .env
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Arquivo .env não encontrado")
        print("   1. Copie: cp .env.example .env")
        print("   2. Configure sua Google Maps API key")
        return False
    else:
        print("✅ Arquivo .env encontrado")
    
    # Test system
    print("\\nTestando sistema...")
    success = run_command("python status_check.py", "Status check")
    
    if success:
        print("\\n🎉 Sistema pronto!")
        print("\\nPróximos comandos:")
        print("  python leadextractor.py extract --sector technology --limit 5")
        print("  python leadextractor.py pipeline --sector banking --limit 10")
        print("  python leadextractor.py start-api")
    else:
        print("\\n⚠️  Configure APIs no arquivo .env primeiro")
    
    return success

if __name__ == "__main__":
    quick_start()
"""
    
    with open('quick_start.py', 'w', encoding='utf-8') as f:
        f.write(script)
    
    print("Criado: quick_start.py")

def main():
    """Cria todos os arquivos de produção"""
    print("=== CRIANDO ARQUIVOS DE PRODUÇÃO ===")
    
    create_deployment_guide()
    create_docker_files()
    create_quick_start()
    
    print("\\n🎉 Arquivos de produção criados!")
    print("\\nArquivos criados:")
    print("  - DEPLOYMENT.md (guia completo)")
    print("  - Dockerfile, docker-compose.yml (.dockerignore)")
    print("  - quick_start.py (setup automático)")
    print("\\nPróximo passo: Teste sua Google Maps API removendo restrições IP")

if __name__ == "__main__":
    main()