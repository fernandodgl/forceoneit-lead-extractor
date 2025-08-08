# ForceOneIT Lead Extractor

Sistema inteligente de extração e qualificação de leads B2B para empresas brasileiras interessadas em soluções AWS.

## 🎯 Objetivo

Automatizar a identificação e qualificação de leads potenciais para a Force One IT, focando em empresas brasileiras de médio e grande porte que possam se beneficiar de soluções AWS.

## 🚀 Funcionalidades

### 🎯 **Extração Inteligente de Leads**
- **Google Maps API**: Busca empresas por setor e localização
- **LinkedIn Sales Navigator**: Extração de empresas e decision makers
- **Extração de Contatos B2B**: Emails e telefones corporativos verificados
- **Social Media Links**: LinkedIn, Facebook, Twitter

### 💎 **Enriquecimento de Dados**
- **CNPJ Integration**: Dados da Receita Federal (ReceitaWS)
- **Tecnografias**: Stack tecnológico das empresas (AWS, Azure, GCP)
- **Buyer Intent Signals**: Análise de intenção de compra
- **Cloud Maturity Assessment**: Nível de adoção de cloud computing

### 🤖 **Inteligência Artificial**
- **Prospect Playlists**: Listas inteligentes personalizadas
- **Daily Recommendations**: Sugestões diárias baseadas em IA
- **Job Change Alerts**: Monitoramento de mudanças de cargo
- **Predictive Scoring**: Score preditivo de fechamento

### 🔗 **Integrações**
- **HubSpot CRM**: Sync automático de empresas, contatos e deals
- **REST API**: Integração em tempo real
- **Webhook Support**: Notificações automáticas

### 🛡️ **Compliance LGPD**
- **Gestão de Consentimento**: Controle total de bases legais
- **Data Subject Rights**: Portabilidade e esquecimento
- **Audit Trail**: Histórico completo de processamento
- **Retention Management**: Anonimização automática

## 📋 Setores-Alvo

- 🏦 **Banking & Fintech**
- 🛍️ **Retail & E-commerce**
- 🏭 **Manufacturing**
- ⛏️ **Mining**
- 💻 **Technology**
- 🏥 **Healthcare**

## 🛠️ Tecnologias

- Python 3.9+
- SQLite para cache local
- APIs: LinkedIn, Google Maps, ReceitaWS
- Pandas para manipulação de dados
- Click para CLI

## 📦 Instalação

```bash
# Clone o repositório
git clone https://github.com/fernandodgl/forceoneit-lead-extractor.git

# Entre no diretório
cd forceoneit-lead-extractor

# Crie ambiente virtual
python -m venv venv

# Ative o ambiente
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
```

## 🔧 Configuração

1. Copie o arquivo `.env.example` para `.env`
2. Configure as API keys necessárias
3. Ajuste os parâmetros de busca em `config.yaml`

## 💡 Uso

### 🔥 **Comandos Principais**
```bash
# Pipeline completo com HubSpot
python leadextractor.py pipeline --sector banking --sync-hubspot --export excel

# Extração básica
python leadextractor.py extract --sector technology --location "São Paulo" --limit 50

# Enriquecimento avançado
python leadextractor.py enrich leads.json --contacts --technographics

# Scoring e sync HubSpot
python leadextractor.py score enriched_leads.json --format excel
python leadextractor.py sync-hubspot scored_leads.json --min-score 70
```

### 🤖 **Funcionalidades IA**
```bash
# Recomendações diárias
python leadextractor.py daily-recommendations --limit 10

# Playlists inteligentes
python leadextractor.py playlist-recommendations

# Monitoramento de mudanças de cargo
python leadextractor.py monitor-job-changes --days 7
```

### 🛡️ **Compliance LGPD**
```bash
# Relatório de compliance
python leadextractor.py compliance-report

# Gerenciar consentimento
python leadextractor.py manage-consent --email exemplo@empresa.com --status revoked
```

### 🚀 **API REST**
```bash
# Iniciar servidor API
python leadextractor.py start-api --host 0.0.0.0 --port 5000
```

## 📊 Critérios de Scoring

O sistema pontua leads baseado em:
- Porte da empresa (faturamento/funcionários)
- Maturidade digital
- Uso atual de cloud
- Potencial de migração AWS
- Fit com casos de sucesso Force One IT

## 🤝 Sobre a Force One IT

Parceiro AWS Advanced Tier desde 2011, especializada em:
- Migração AWS
- Gestão de Custos (FinOps)
- Managed Services
- Suporte 24/7

## 📄 Licença

Proprietary - Force One IT © 2024