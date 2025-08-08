# ForceOneIT Lead Extractor

Sistema inteligente de extração e qualificação de leads B2B para empresas brasileiras interessadas em soluções AWS.

## 🎯 Objetivo

Automatizar a identificação e qualificação de leads potenciais para a Force One IT, focando em empresas brasileiras de médio e grande porte que possam se beneficiar de soluções AWS.

## 🚀 Funcionalidades

- **Extração Multi-fonte**: Coleta dados de LinkedIn, Google Maps, e bases públicas
- **Enriquecimento de Dados**: CNPJ, porte da empresa, setor de atuação
- **Scoring Inteligente**: Qualificação baseada em critérios AWS e fit com Force One IT
- **Segmentação por Setor**: Foco em Banking, Retail, Manufacturing, Mining, Tech, Healthcare
- **Exportação Flexível**: CSV, Excel, integração com CRMs

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

```bash
# Buscar leads no setor bancário
python leadextractor.py extract --sector banking --size large

# Enriquecer dados de empresas
python leadextractor.py enrich --input leads.csv

# Calcular score de qualificação
python leadextractor.py score --input enriched_leads.csv

# Pipeline completo
python leadextractor.py pipeline --sector all --export excel
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