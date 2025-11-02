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
import base64 # <<<<<<< IMPORTANTE: Adicione este import para Base64

# --- 1. Configuração e Autenticação com o Google BigQuery ---

credentials = None
project_id = None

# Caminho para o arquivo de credenciais local (para desenvolvimento)
CREDENTIALS_PATH_LOCAL = 'credentials/chave-de-servico.json'

# --- Lógica de Carregamento de Credenciais ---

# 1. Tentar carregar credenciais do arquivo local (prioridade para desenvolvimento)
if os.path.exists(CREDENTIALS_PATH_LOCAL):
    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH_LOCAL)
        project_id = credentials.project_id
        # st.info("DEBUG: Credenciais carregadas do arquivo local para desenvolvimento.") # Comentado para evitar poluir o app
    except Exception as e:
        st.error(f"Erro ao carregar credenciais do arquivo local '{CREDENTIALS_PATH_LOCAL}': {e}")
        st.error("Verifique se o arquivo JSON está válido e as permissões.")
        st.stop()
else:
    # 2. Se não encontrou o arquivo local, tentar carregar dos Streamlit Secrets (Base64)
    try:
        if "GOOGLE_APPLICATION_CREDENTIALS" in st.secrets:
            # Assume que o secret agora é uma string Base64 do JSON
            base64_encoded_json = st.secrets["GOOGLE_APPLICATION_CREDENTIALS"]
            
            # <<<<<<< IMPORTANTE: Decodifica de Base64 para bytes, depois para string UTF-8
            decoded_json_bytes = base64.b64decode(base64_encoded_json)
            service_account_info_str = decoded_json_bytes.decode('utf-8')
            
            # Converte a string JSON para dicionário
            credentials_info = json.loads(service_account_info_str)
            
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            project_id = credentials_info.get("project_id")
            # st.info("DEBUG: Credenciais carregadas e decodificadas de Base64 dos Streamlit Secrets (ambiente de deploy).") # Comentado
            # st.info(f"DEBUG: Project ID carregado: {project_id}") # Comentado
        else:
            st.error("ERRO: Credenciais 'GOOGLE_APPLICATION_CREDENTIALS' não encontradas nos Streamlit Secrets.")
            st.error("Certifique-se de configurar GOOGLE_APPLICATION_CREDENTIALS na interface do Streamlit Cloud.")
            st.stop()
    except StreamlitSecretNotFoundError:
        st.error(f"ERRO: Credenciais não carregadas. Nenhum arquivo secrets.toml encontrado localmente "
                 f"e o arquivo '{CREDENTIALS_PATH_LOCAL}' também não existe.")
        st.error("Para desenvolvimento local, coloque 'chave-de-servico.json' em 'credentials/'.")
        st.error("Para deploy, configure 'GOOGLE_APPLICATION_CREDENTIALS' nos Secrets do Streamlit Cloud (agora como Base64).")
        st.stop()
    except Exception as e:
        st.error(f"Erro inesperado ao carregar credenciais do Streamlit Secrets (possivelmente problema de Base64 ou JSON): {e}")
        st.stop()

# Se chegamos até aqui e as credenciais foram carregadas com sucesso, podemos criar o cliente BigQuery.
if credentials and project_id:
    client = bigquery.Client(credentials=credentials, project=project_id)
    # st.info("DEBUG: Cliente BigQuery inicializado com sucesso.") # Comentado
else:
    st.error("ERRO FATAL: Credenciais ou Project ID não foram carregados com sucesso. Verifique a configuração.")
    st.stop()


# --- Restante das Constantes e Funções Auxiliares ---
TAXA_ADWORK_PERCENT = 0.17 # 17% (a taxa percentual em si, usada para cálculo)
DEFAULT_USD_BRL_RATE = 5.00 # Cotação padrão para caso a API falhe

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
        return f"R${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
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
            # Evita divisão por zero quando o valor anterior é 0 e o atual não
            return None # Indica delta indeterminado
    
    delta = ((current_val_num - previous_val_num) / previous_val_num) * 100
    return delta


def calculate_business_metrics(df, default_taxa_adwork_percent=TAXA_ADWORK_PERCENT):
    """
    Calcula todas as métricas de negócio e mídia a partir de um DataFrame.
    """
    numeric_cols_to_fill = [
        'total_impressoes', 'total_cliques', 'total_custo',
        'total_receita', 'total_leads', 'total_mensagens'
    ]

    df_processed = df.copy()

    for col in numeric_cols_to_fill:
        if col in df_processed.columns:
            df_processed[col] = df_processed[col].fillna(0)
        else:
            df_processed[col] = 0.0

    total_impressoes = df_processed['total_impressoes'].sum()
    total_cliques = df_processed['total_cliques'].sum()
    total_custo = df_processed['total_custo'].sum()
    total_receita = df_processed['total_receita'].sum()

    total_receita = float(total_receita)
    total_custo = float(total_custo)

    custo_taxa_adwork = total_receita * default_taxa_adwork_percent
    lucro_liquido = total_receita - total_custo - custo_taxa_adwork

    roi = 0.0
    roas = 0.0
    if total_custo != 0:
        roi = ((total_receita - total_custo) / total_custo) * 100
        roas = (total_receita / total_custo) * 100
    # Se custo é 0 mas há receita, ROI/ROAS é considerado infinito
    elif total_receita > 0:
        roi = float('inf')
        roas = float('inf')
    
    return {
        'total_impressoes': total_impressoes,
        'total_cliques': total_cliques,
        'total_custo': total_custo,
        'total_receita': total_receita,
        'lucro_liquido': lucro_liquido,
        'roi': roi,
        'roas': roas,
        'custo_taxa_adwork': custo_taxa_adwork
    }

# --- Função para Carregar Dados do BigQuery ---
@st.cache_data(ttl=3600) # Cache os dados por 1 hora (3600 segundos)
def get_data_from_bigquery(query_sql):
    """
    Executa uma consulta SQL no BigQuery e retorna os resultados em um DataFrame Pandas.
    """
    try:
        query_job = client.query(query_sql)
        with st.spinner("Carregando dados do BigQuery..."):
            df = query_job.to_dataframe()
            # Garante que a coluna 'data' seja do tipo datetime, essencial para Plotly e formatação
            if 'data' in df.columns:
                df['data'] = pd.to_datetime(df['data'])
            
            # Garante que as novas colunas existam, mesmo que vazias, para evitar KeyError
            for col in ['utm_campaign_norm', 'pais']:
                if col not in df.columns:
                    df[col] = None # Define como None, que será tratado como NaN pelo Pandas
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta BigQuery: {e}")
        st.warning("Verifique sua consulta SQL e as permissões da conta de serviço no BigQuery.")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache os dados por 1 hora (3600 segundos)
def load_data_for_period(start_date, end_date):
    """
    Carrega dados do BigQuery para o período especificado, unindo Meta Ads e Admanager.
    Incorpora a lógica de UTM e domínio canônico fornecida pelo usuário.
    Converte receita do Admanager de USD para BRL.
    Retorna o DataFrame completo (sem filtro de domínio/utm/país ainda).
    """
    meta_ads_campaign_insights_table = f"`{project_id}.facebook_ads_data.campaign_insights`"
    ad_manager_universal_table = f"`{project_id}.ad_manager.admanager_universal`"
    ad_manager_utms_units_table = f"`{project_id}.ad_manager.admanager_utms_units`"

    # Formata as datas para a consulta SQL
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    query = f"""
    WITH agg AS (
      SELECT
        COALESCE(adx_ad_unit, ad_unit) AS ad_unit_key,
        domain,
        SUM(impressions) AS imp
      FROM {ad_manager_universal_table}
      WHERE domain IS NOT NULL AND domain <> ''
        AND date BETWEEN '{start_date_str}' AND '{end_date_str}'
      GROUP BY 1, 2
    ),
    ranked AS (
      SELECT
        ad_unit_key, domain, imp,
        ROW_NUMBER() OVER (PARTITION BY ad_unit_key ORDER BY imp DESC) AS rn
      FROM agg
    ),
    dim_adunit AS (
      SELECT ad_unit_key, domain
      FROM ranked
      WHERE rn = 1
    ),

    -- 2) UTM de campanha por domínio (derivado de ad_manager.admanager_utms_units)
    utm_campaign_by_domain AS (
      SELECT
        u.date                                                 AS data,
        LOWER(TRIM(COALESCE(u.utm_value, u.utm_value_api)))   AS utm_campaign_norm,
        d.domain                                              AS dominio,
        SUM(u.impressions) AS adm_imp,
        SUM(u.clicks)      AS adm_clk,
        SUM(u.revenue)     AS adm_rev
      FROM {ad_manager_utms_units_table} u
      LEFT JOIN dim_adunit d
        ON d.ad_unit_key = COALESCE(u.adx_ad_unit, u.ad_unit)
      WHERE u.date BETWEEN '{start_date_str}' AND '{end_date_str}'
        AND u.utm_key = 'utm_campaign'
      GROUP BY 1,2,3
    ),

    -- 3) Bloco do Admanager (UTM) no shape final (como você já estava usando)
    admanager_utm AS (
      SELECT
        CAST(u.date AS DATE)                    AS data,
        CAST('Admanager (UTM)' AS STRING)       AS source,
        CAST(NULL AS STRING)                    AS pais, -- Explicitamente NULL conforme a query fornecida
        CAST(d.domain AS STRING)                AS dominio,
        LOWER(TRIM(COALESCE(u.utm_value, u.utm_value_api))) AS utm_campaign_norm, -- Adicionado UTM da Admanager
        CAST(SUM(u.impressions) AS INT64)       AS total_impressoes,
        CAST(SUM(u.clicks) AS INT64)            AS total_cliques,
        CAST(NULL AS FLOAT64)                   AS total_custo, -- Custo não é da Admanager aqui
        CAST(SUM(u.revenue) AS FLOAT64)         AS total_receita,  -- USD (moeda da rede)
        CAST(NULL AS INT64)                     AS total_leads,
        CAST(NULL AS INT64)                     AS total_mensagens
      FROM {ad_manager_utms_units_table} u
      LEFT JOIN dim_adunit d
        ON d.ad_unit_key = COALESCE(u.adx_ad_unit, u.ad_unit)
      WHERE u.date BETWEEN '{start_date_str}' AND '{end_date_str}'
      GROUP BY 1,2,3,4, utm_campaign_norm -- utm_campaign_norm adicionado ao GROUP BY
    ),

    -- 4) Meta Ads ligado por campanha à malha de domínios do Admanager
    meta_ads_joined AS (
      SELECT
        CAST(m.Date AS DATE)                                       AS data,
        CAST('Meta Ads' AS STRING)                                 AS source,
        CAST(NULL AS STRING)                                       AS pais, -- Explicitamente NULL conforme a query fornecida
        CAST(u.dominio AS STRING)                                  AS dominio,
        LOWER(TRIM(m.Campaign_Name))                               AS utm_campaign_norm, -- UTM do Meta Ads
        CAST(SUM(m.Impressions) AS INT64)                          AS total_impressoes,
        CAST(SUM(m.Clicks) AS INT64)                               AS total_cliques,
        CAST(SUM(m.Spend) AS FLOAT64)                              AS total_custo,
        CAST(NULL AS FLOAT64)                                      AS total_receita, -- Receita não vem do Meta Ads neste join
        CAST(SUM(m.Leads) AS INT64)                                AS total_leads,
        CAST(SUM(m.Messages) AS INT64)                             AS total_mensagens
      FROM {meta_ads_campaign_insights_table} m
      LEFT JOIN utm_campaign_by_domain u
        ON u.data = CAST(m.Date AS DATE)
       AND u.utm_campaign_norm = LOWER(TRIM(m.Campaign_Name))
      WHERE m.Date BETWEEN '{start_date_str}' AND '{end_date_str}'
      GROUP BY 1,2,3,4, utm_campaign_norm
    )

    -- 5) UNION das duas fontes, já padronizadas
    SELECT * FROM meta_ads_joined
    UNION ALL
    SELECT * FROM admanager_utm
    ORDER BY data, source, pais, dominio, utm_campaign_norm
    """
    df = get_data_from_bigquery(query)

    if not df.empty:
        usd_to_brl_rate = get_usd_to_brl_rate()
        
        # Converte a receita que vem do Admanager (agora marcado como source 'Admanager (UTM)')
        df['total_receita'] = pd.to_numeric(df['total_receita'], errors='coerce').fillna(0)
        df.loc[df['source'] == 'Admanager (UTM)', 'total_receita'] *= usd_to_brl_rate
        
    return df