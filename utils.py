# utils.py
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
import json # Adicione este import para lidar com JSON
from streamlit.errors import StreamlitSecretNotFoundError # Importe o erro específico do Streamlit

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
        #st.success("Credenciais carregadas do arquivo local para desenvolvimento.")
    except Exception as e:
        st.error(f"Erro ao carregar credenciais do arquivo local '{CREDENTIALS_PATH_LOCAL}': {e}")
        st.error("Verifique se o arquivo JSON está válido e as permissões.")
        st.stop()
else:
    # 2. Se não encontrou o arquivo local, tentar carregar dos Streamlit Secrets
    #    (para deploy no Streamlit Cloud ou para dev com secrets.toml)
    try:
        # Verifica se a chave está presente nos secrets
        if "GOOGLE_APPLICATION_CREDENTIALS" in st.secrets:
            # Carrega a string JSON do secret e converte para dicionário
            credentials_info = json.loads(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            project_id = credentials_info.get("project_id") # O project_id está dentro do JSON
            st.success("Credenciais carregadas do Streamlit Secrets (ambiente de deploy).")
        else:
            st.error("ERRO: Credenciais 'GOOGLE_APPLICATION_CREDENTIALS' não encontradas nos Streamlit Secrets.")
            st.error("Certifique-se de configurar GOOGLE_APPLICATION_CREDENTIALS na interface do Streamlit Cloud.")
            st.stop()
    except StreamlitSecretNotFoundError:
        # Este erro acontece se não há nenhum arquivo secrets.toml/secret dir localmente.
        # É esperado quando rodando localmente sem um secrets.toml e sem o arquivo local de credenciais.
        st.error(f"ERRO: Credenciais não carregadas. Nenhum arquivo secrets.toml encontrado localmente "
                 f"e o arquivo '{CREDENTIALS_PATH_LOCAL}' também não existe.")
        st.error("Para desenvolvimento local, coloque 'chave-de-servico.json' em 'credentials/'.")
        st.error("Para deploy, configure 'GOOGLE_APPLICATION_CREDENTIALS' nos Secrets do Streamlit Cloud.")
        st.stop()
    except Exception as e:
        # Captura outros erros inesperados ao carregar de st.secrets
        st.error(f"Erro inesperado ao carregar credenciais do Streamlit Secrets: {e}")
        st.stop()

# Se chegamos até aqui e as credenciais foram carregadas com sucesso, podemos criar o cliente BigQuery.
if credentials and project_id:
    client = bigquery.Client(credentials=credentials, project=project_id)
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
        st.warning(f"Não foi possível obter a cotação USD-BRL da API: {e}. Usando cotação padrão: R\$ {DEFAULT_USD_BRL_RATE:,.2f}")
        return DEFAULT_USD_BRL_RATE
    except (KeyError, TypeError) as e:
        st.warning(f"Erro ao processar a resposta da API de cotação: {e}. Usando cotação padrão: R\$ {DEFAULT_USD_BRL_RATE:,.2f}")
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
        return f"R\${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
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
            return None # Não é possível calcular variação de 0 para um valor não-zero
    
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
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta BigQuery: {e}")
        st.warning("Verifique sua consulta SQL e as permissões da conta de serviço no BigQuery.")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache os dados por 1 hora (3600 segundos)
def load_data_for_period(start_date, end_date):
    """
    Carrega dados do BigQuery para o período especificado, unindo Meta Ads e Admanager.
    Converte receita do Admanager de USD para BRL.
    Retorna o DataFrame completo (sem filtro de domínio ainda).
    """
    meta_ads_table = f"`{project_id}.facebook_ads_data.campaign_insights`"
    ad_manager_table = f"`{project_id}.ad_manager.admanager_universal`"

    query = f"""
    SELECT
        data,
        source,
        pais,
        dominio,
        SUM(total_impressoes) AS total_impressoes,
        SUM(total_cliques) AS total_cliques,
        SUM(total_custo) AS total_custo,
        SUM(total_receita) AS total_receita, -- Este valor vem em USD
        SUM(total_leads) AS total_leads,
        SUM(total_mensagens) AS total_mensagens
    FROM (
        -- Consulta para Meta Ads
        SELECT
            Date AS data,
            'Meta Ads' AS source,
            NULL AS pais,
            NULL AS dominio,
            SUM(Impressions) AS total_impressoes,
            SUM(Clicks) AS total_cliques,
            SUM(Spend) AS total_custo,
            NULL AS total_receita,
            SUM(Leads) AS total_leads,
            SUM(Messages) AS total_mensagens
        FROM
            {meta_ads_table}
        WHERE
            Date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        GROUP BY
            data

        UNION ALL

        -- Consulta para Admanager
        SELECT
            date AS data,
            'Admanager' AS source,
            country AS pais,
            domain AS dominio,
            SUM(impressions) AS total_impressoes,
            SUM(clicks) AS total_cliques,
            NULL AS total_custo,
            SUM(revenue) AS total_receita, -- Este valor vem em USD
            NULL AS total_leads,
            NULL AS total_mensagens
        FROM
            {ad_manager_table}
        WHERE
            date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
        GROUP BY
            date, country, domain
    )
    GROUP BY
        data, source, pais, dominio
    ORDER BY
        data, source, pais, dominio
    """
    df = get_data_from_bigquery(query)

    if not df.empty:
        usd_to_brl_rate = get_usd_to_brl_rate()
        
        df['total_receita'] = pd.to_numeric(df['total_receita'], errors='coerce').fillna(0)
        df.loc[df['source'] == 'Admanager', 'total_receita'] *= usd_to_brl_rate
        
    return df
