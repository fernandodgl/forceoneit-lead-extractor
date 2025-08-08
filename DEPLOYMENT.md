# 🚀 FORCE ONE IT LEAD EXTRACTOR - DEPLOYMENT GUIDE

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
