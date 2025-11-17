# utils.py
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
import json
from streamlit.errors import StreamlitSecretNotFoundError
import base64

# --- 1. Configuração e Autenticação com o Google BigQuery ---

credentials = None
project_id = "dashboard-474222" # Definido explicitamente com base nas tabelas fornecidas

# Caminho para o arquivo de credenciais local (para desenvolvimento)
CREDENTIALS_PATH_LOCAL = 'credentials/chave-de-servico.json'

# --- Lógica de Carregamento de Credenciais ---

# 1. Tentar carregar credenciais do arquivo local (prioridade para desenvolvimento)
if os.path.exists(CREDENTIALS_PATH_LOCAL):
    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH_LOCAL)
        if credentials.project_id != project_id:
             st.warning(f"O project_id nas credenciais locais ({credentials.project_id}) difere do project_id esperado ({project_id}). Usando o project_id das credenciais.")
             project_id = credentials.project_id
        # st.info("DEBUG: Credenciais carregadas do arquivo local para desenvolvimento.")
    except Exception as e:
        st.error(f"Erro ao carregar credenciais do arquivo local '{CREDENTIALS_PATH_LOCAL}': {e}")
        st.error("Verifique se o arquivo JSON está válido e as permissões.")
        st.stop()
else:
    # 2. Se não encontrou o arquivo local, tentar carregar dos Streamlit Secrets (Base64)
    try:
        if "GOOGLE_APPLICATION_CREDENTIALS" in st.secrets:
            base64_encoded_json = st.secrets["GOOGLE_APPLICATION_CREDENTIALS"]
            decoded_json_bytes = base64.b64decode(base64_encoded_json)
            service_account_info_str = decoded_json_bytes.decode('utf-8')
            credentials_info = json.loads(service_account_info_str)
            
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            if credentials_info.get("project_id") != project_id:
                st.warning(f"O project_id nas credenciais dos secrets ({credentials_info.get('project_id')}) difere do project_id esperado ({project_id}). Usando o project_id das credenciais.")
                project_id = credentials_info.get("project_id")
            # st.info("DEBUG: Credenciais carregadas e decodificadas de Base64 dos Streamlit Secrets (ambiente de deploy).")
        else:
            st.error("ERRO: Credenciais 'GOOGLE_APPLICATION_CREDENTIALS' não encontradas nos Streamlit Secrets.")
            st.error("Certifique-se de configurar GOOGLE_APPLICATION_CREDENTIALS nos Secrets do Streamlit Cloud (agora como Base64).")
            st.stop()
    except StreamlitSecretNotFoundError:
        st.error(f"ERRO: Credenciais não carregadas. Nenhum arquivo secrets.toml encontrado localmente "
                 f"e o arquivo '{CREDENTIALS_PATH_PATH}' também não existe.")
        st.error("Para desenvolvimento local, coloque 'chave-de-servico.json' em 'credentials/'.")
        st.error("Para deploy, configure 'GOOGLE_APPLICATION_CREDENTIALS' nos Secrets do Streamlit Cloud (agora como Base64).")
        st.stop()
    except Exception as e:
        st.error(f"Erro inesperado ao carregar credenciais do Streamlit Secrets (possivelmente problema de Base64 ou JSON): {e}")
        st.stop()

# Se chegamos até aqui e as credenciais foram carregadas com sucesso, podemos criar o cliente BigQuery.
if credentials and project_id:
    client = bigquery.Client(credentials=credentials, project=project_id)
    # st.info("DEBUG: Cliente BigQuery inicializado com sucesso.")
else:
    st.error("ERRO FATAL: Credenciais ou Project ID não foram carregados com sucesso. Verifique a configuração.")
    st.stop()


# --- Restante das Constantes ---
TAXA_ADWORK_PERCENT = 0.17 # 17% (a taxa percentual em si, usada para cálculo)
DEFAULT_USD_BRL_RATE = 5.00 # Cotação padrão para caso a API falhe

# --- Nomes das Tabelas BigQuery (COM OS CAMINHOS COMPLETOS FORNECIDOS) ---
# <<<<<<< ESTAS VARIÁVEIS PRECISAM ESTAR AQUI, ANTES DE serem usadas nas funções >>>>>>>
ADX_DOMAIN_UTMS_TABLE = "`dashboard-474222.ad_manager.adx_domain_with_utms_daily`"
CAMPAIGN_INSIGHTS_TABLE = "`dashboard-474222.facebook_ads_data.campaign_insights`"


# --- FUNÇÕES AUXILIARES ---

@st.cache_data(ttl=datetime.timedelta(hours=24)) # Cache a cotação por 24 horas
def get_usd_to_brl_rate():
    """
    Busca a cotação atual de USD para BRL usando a API do Frankfurter.
    Retorna a cotação ou um valor padrão em caso de erro.
    """
    try:
        response = requests.get("https://api.frankfurter.app/latest?from=USD&to=BRL")
        response.raise_for_status() # Lança um erro para códigos de status HTTP ruins (4xx ou 5xx)
        data = response.json()
        rate = data['rates']['BRL']
        return rate
    except requests.exceptions.RequestException as e:
        st.warning(f"Não foi possível obter a cotação USD-BRL da API: {e}. Usando cotação padrão: R$ {DEFAULT_USD_BRL_RATE:,.2f}")
        return DEFAULT_USD_BRL_RATE
    except (KeyError, TypeError) as e:
        st.warning(f"Erro ao processar a resposta da API de cotação: {e}. Usando cotação padrão: R$ {DEFAULT_USD_BRL_RATE:,.2f}")
        return DEFAULT_USD_BRL_RATE


def format_number(value, currency=False, percentage=False, decimal_places=0):
    if pd.isna(value) or value is None:
        return "N/A"
    
    # Handle infinite values from numpy or direct float('inf')
    if isinstance(value, float) and (np.isinf(value) or value == float('inf')):
        return "Inf" + ("%" if percentage else "")

    if percentage:
        return f"{value:,.{decimal_places}f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    if currency:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calculate_percentage_delta(current_value, previous_value):
    """
    Calcula a variação percentual entre o valor atual e o anterior.
    Retorna None se a comparação não for possível (dados ausentes ou divisão por zero).
    """
    current_val_num = 0.0 if pd.isna(current_value) or current_value is None else float(current_value)
    previous_val_num = 0.0 if pd.isna(previous_value) or previous_value is None else float(previous_value)

    if previous_val_num == 0:
        if current_val_num == 0:
            return 0.0 # Sem mudança (0 para 0)
        else:
            return None 
    
    delta = ((current_val_num - previous_val_num) / previous_val_num) * 100
    return delta


def calculate_business_metrics(df, default_taxa_adwork_percent=TAXA_ADWORK_PERCENT):
    """
    Calcula todas as métricas de negócio e mídia a partir de um DataFrame.
    MODIFICAÇÃO: 'total_leads' agora é a soma de leads e mensagens.
    """
    numeric_cols_to_fill = [
        'total_impressoes', 'total_cliques', 'total_custo',
        'total_receita', 'total_leads', 'total_mensagens'
    ]

    df_processed = df.copy()

    for col in numeric_cols_to_fill:
        if col in df_processed.columns:
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0)
        else:
            df_processed[col] = 0.0

    total_impressoes = df_processed['total_impressoes'].sum()
    total_cliques = df_processed['total_cliques'].sum()
    total_custo = df_processed['total_custo'].sum()
    total_receita = df_processed['total_receita'].sum()
    
    # MODIFICAÇÃO AQUI: total_leads agora é a soma de leads e mensagens
    total_leads_original = df_processed['total_leads'].sum() # Salva leads originais caso precise
    total_mensagens = df_processed['total_mensagens'].sum()
    total_leads_combined = total_leads_original + total_mensagens # Nova métrica combinada

    total_receita = float(total_receita)
    total_custo = float(total_custo)

    custo_taxa_adwork = total_receita * default_taxa_adwork_percent
    lucro_liquido = total_receita - total_custo - custo_taxa_adwork

    roi = 0.0
    roas = 0.0
    if total_custo != 0:
        roi = ((total_receita - total_custo) / total_custo) * 100
        roas = (total_receita / total_custo)
    elif total_receita > 0:
        roi = np.nan # Use np.nan para ROI indefinido
        roas = np.nan # Use np.nan para ROAS indefinido
        
    cpm = (total_custo / total_impressoes * 1000) if total_impressoes != 0 else 0
    cpc = (total_custo / total_cliques) if total_cliques != 0 else 0
    ctr = (total_cliques / total_impressoes * 100) if total_impressoes != 0 else 0
    
    # MODIFICAÇÃO AQUI: CPL usa a nova métrica combinada
    cpl = (total_custo / total_leads_combined) if total_leads_combined != 0 else 0

    return {
        'total_impressoes': total_impressoes,
        'total_cliques': total_cliques,
        'total_custo': total_custo,
        'total_receita': total_receita,
        'lucro_liquido': lucro_liquido,
        'roi': roi,
        'roas': roas,
        'custo_taxa_adwork': custo_taxa_adwork,
        'total_leads': total_leads_combined, # Retorna a métrica combinada como 'total_leads'
        'total_mensagens': total_mensagens, # Mantém mensagens separadas no retorno
        'cpm': cpm,
        'cpc': cpc,
        'ctr': ctr,
        'cpl': cpl
    }

# --- Função para Carregar Dados do BigQuery (Generalizada) ---
@st.cache_data(ttl=3600)
def get_data_from_bigquery(query_sql):
    """
    Executa uma consulta SQL no BigQuery e retorna os resultados em um DataFrame Pandas.
    """
    try:
        query_job = client.query(query_sql)
        with st.spinner("Carregando dados do BigQuery..."):
            df = query_job.to_dataframe()
            if 'data' in df.columns:
                df['data'] = pd.to_datetime(df['data'])
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta BigQuery: {e}")
        st.warning("Verifique sua consulta SQL e as permissões da conta de serviço no BigQuery.")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_data_for_period(start_date, end_date):
    """
    Carrega dados do BigQuery para o período especificado, unindo dados de Admanager
    e insights de campanha (Meta Ads) via FULL OUTER JOIN.
    Assume que revenue da tabela adx_domain_utms_daily está em USD e spend da campaign_insights está em BRL.
    Converte receita do Admanager de USD para BRL.
    Retorna o DataFrame completo.
    """
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    query_combined = f"""
    WITH AdX_Formatted AS (
        SELECT
            FORMAT_DATE('%Y-%m-%d', adx.date) AS data,
            adx.country AS pais,
            adx.domain AS dominio,
            adx.network_code AS network_code,
            adx.impressions AS adx_impressions,
            adx.clicks AS adx_clicks,
            adx.revenue AS adx_revenue_usd, -- Renomeado para indicar USD
            LOWER(TRIM(adx.utm_campaign)) AS utm_campaign_norm,
            LOWER(TRIM(adx.utm_source)) AS utm_source,
            LOWER(TRIM(adx.utm_medium)) AS utm_medium,
            LOWER(TRIM(adx.utm_content)) AS utm_content,
            LOWER(TRIM(adx.utm_term)) AS utm_term,
            LOWER(TRIM(adx.utm_id)) AS utm_id
        FROM
            {ADX_DOMAIN_UTMS_TABLE} AS adx
        WHERE
            adx.date BETWEEN '{start_date_str}' AND '{end_date_str}'
    ),
    CI_Formatted AS (
        SELECT
            FORMAT_DATE('%Y-%m-%d', ci.date) AS data,
            LOWER(TRIM(ci.campaign_name)) AS campaign_name_norm,
            ci.spend AS ci_spend,
            ci.leads AS ci_leads,
            ci.messages AS ci_messages,
            ci.impressions AS ci_impressions, 
            ci.clicks AS ci_clicks
        FROM
            {CAMPAIGN_INSIGHTS_TABLE} AS ci
        WHERE
            ci.date BETWEEN '{start_date_str}' AND '{end_date_str}'
    )
    SELECT
        COALESCE(adx.data, ci.data) AS data,
        CASE
            WHEN adx.utm_campaign_norm IS NOT NULL AND ci.campaign_name_norm IS NOT NULL THEN 'Admanager (UTM) & Meta Ads'
            WHEN adx.utm_campaign_norm IS NOT NULL THEN 'Admanager (UTM)'
            WHEN ci.campaign_name_norm IS NOT NULL THEN 'Meta Ads'
            ELSE 'Unknown' -- Caso algo dê muito errado, mas não deve acontecer com WHERE
        END AS source,
        -- Colunas que vêm predominantemente do AdX, serão NULL para Meta Ads-only
        COALESCE(adx.pais, 'N/A') AS pais,
        COALESCE(adx.dominio, 'N/A') AS dominio,
        COALESCE(adx.network_code, 'N/A') AS network_code,
        
        -- Métricas: AGORA COALESCE SOMA IMPRESSÕES E CLIQUES DE AMBAS AS FONTES
        COALESCE(adx.adx_impressions, 0) + COALESCE(ci.ci_impressions, 0) AS total_impressoes,
        COALESCE(adx.adx_clicks, 0) + COALESCE(ci.ci_clicks, 0) AS total_cliques,
        COALESCE(ci.ci_spend, 0) AS total_custo, -- Custo vem só de Campaign Insights
        COALESCE(adx.adx_revenue_usd, 0) AS total_receita, -- Receita vem só de AdX (USD)
        COALESCE(ci.ci_leads, 0) AS total_leads, -- Leads vem só de Campaign Insights
        COALESCE(ci.ci_messages, 0) AS total_mensagens, -- Mensagens vem só de Campaign Insights
        
        -- UTMs: usar a versão normalizada da campanha e os outros UTMs do AdX
        COALESCE(adx.utm_campaign_norm, ci.campaign_name_norm) AS utm_campaign_norm,
        COALESCE(adx.utm_source, 'N/A') AS utm_source,
        COALESCE(adx.utm_medium, 'N/A') AS utm_medium,
        COALESCE(adx.utm_content, 'N/A') AS utm_content,
        COALESCE(adx.utm_term, 'N/A') AS utm_term,
        COALESCE(adx.utm_id, 'N/A') AS utm_id
    FROM
        AdX_Formatted AS adx
    FULL OUTER JOIN
        CI_Formatted AS ci
    ON
        adx.data = ci.data AND adx.utm_campaign_norm = ci.campaign_name_norm
    """
    
    df_combined = get_data_from_bigquery(query_combined)

    if not df_combined.empty:
        # Converter a receita do Admanager de USD para BRL
        usd_to_brl_rate = get_usd_to_brl_rate()
        if usd_to_brl_rate and usd_to_brl_rate != 0:
            # A conversão aplica-se SOMENTE às linhas que possuem receita original do Admanager (que está em USD)
            # Para as linhas puramente Meta Ads, total_receita será 0 e não será alterada.
            df_combined['total_receita'] = pd.to_numeric(df_combined['total_receita'], errors='coerce').fillna(0) # Garante que é numérico
            df_combined['total_receita'] *= usd_to_brl_rate
        else:
            st.warning("Não foi possível obter a taxa de câmbio USD-BRL. A receita Admanager pode não estar convertida corretamente para BRL.")
            
    # --- Conversões finais de tipos de dados e tratamento de NaNs ---
    numeric_cols = [
        'total_impressoes', 'total_cliques', 'total_custo', 'total_receita',
        'total_leads', 'total_mensagens'
    ]
    for col in numeric_cols:
        df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)

    string_cols = [
        'source', 'pais', 'dominio', 'network_code', 'utm_campaign_norm', 'utm_source', 'utm_medium', 
        'utm_content', 'utm_term', 'utm_id'
    ]
    for col in string_cols:
        if col not in df_combined.columns:
            df_combined[col] = 'N/A'
        df_combined[col] = df_combined[col].fillna('N/A').astype(str)

    return df_combined
