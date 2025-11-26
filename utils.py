# utils.py
import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import os
import numpy as np
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
import json
from streamlit.errors import StreamlitSecretNotFoundError
import base64 # Necessário para decodificar secrets

# --- IMPORTS PARA GOOGLE SHEETS ---
import gspread # Necessário para interagir com Google Sheets

# --- 1. Configuração e Autenticação com o Google BigQuery ---

credentials = None
project_id = "dashboard-474222" # Definido explicitamente com base nas tabelas fornecidas

# Caminho para o arquivo de credenciais local do BigQuery
BQ_CREDENTIALS_PATH_LOCAL = 'credentials/chave-de-servico.json' 

# --- Lógica de Carregamento de Credenciais BigQuery ---

# 1. Tentar carregar credenciais do arquivo local (prioridade para desenvolvimento)
if os.path.exists(BQ_CREDENTIALS_PATH_LOCAL):
    try:
        credentials = service_account.Credentials.from_service_account_file(BQ_CREDENTIALS_PATH_LOCAL)
        if credentials.project_id != project_id:
             st.warning(f"O project_id nas credenciais locais ({credentials.project_id}) difere do project_id esperado ({project_id}). Usando o project_id das credenciais.")
             project_id = credentials.project_id
    except Exception as e:
        st.error(f"❌ Erro ao carregar credenciais BigQuery do arquivo local '{BQ_CREDENTIALS_PATH_LOCAL}': {e}")
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
        else:
            st.error("ERRO: Credenciais 'GOOGLE_APPLICATION_CREDENTIALS' não encontradas nos Streamlit Secrets.")
            st.error("Certifique-se de configurar GOOGLE_APPLICATION_CREDENTIALS nos Secrets do Streamlit Cloud (agora como Base64).")
            st.stop()
    except StreamlitSecretNotFoundError: 
        st.error(f"ERRO: Credenciais BigQuery não carregadas. Nenhum arquivo secrets.toml encontrado localmente "
                 f"e o arquivo '{BQ_CREDENTIALS_PATH_LOCAL}' também não existe.") 
        st.error("Para desenvolvimento local, coloque 'chave-de-servico.json' em 'credentials/'.")
        st.error("Para deploy, configure 'GOOGLE_APPLICATION_CREDENTIALS' nos Secrets do Streamlit Cloud (agora como Base64).")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro inesperado ao carregar credenciais BigQuery do Streamlit Secrets (possivelmente problema de Base64 ou JSON): {e}")
        st.stop()

# Se chegamos até aqui e as credenciais foram carregadas com sucesso, podemos criar o cliente BigQuery.
if credentials and project_id:
    try:
        client = bigquery.Client(credentials=credentials, project=project_id)
    except Exception as e:
        st.error(f"❌ Erro ao inicializar o cliente BigQuery: {e}. Verifique as credenciais e o project ID.")
        st.stop()
else:
    st.error("ERRO FATAL: Credenciais BigQuery ou Project ID não foram carregados com sucesso. Verifique a configuração.")
    st.stop()

# --- SEÇÃO: Configuração e Autenticação com o Google Sheets ---

sheets_gc = None # Objeto gspread.Client

# Caminho para o arquivo de credenciais local do Google Sheets
GSHEETS_CREDENTIALS_PATH_LOCAL = 'credentials/chave-de-servico.json' 
GSHEETS_SPREADSHEET_ID = '1yr4yCLlXAMoMMpyqFpVsZKQ7sfbf7xr3WCJ9BMqYT6k' # ID da sua planilha
GSHEETS_SPREADSHEET_NAME = 'Controle de BMs e CONTAS de anúncio' # Apenas para mensagens de erro/informativas

# --- Lógica de Carregamento de Credenciais Google Sheets ---

if os.path.exists(GSHEETS_CREDENTIALS_PATH_LOCAL):
    try:
        sheets_gc = gspread.service_account(filename=GSHEETS_CREDENTIALS_PATH_LOCAL)
    except Exception as e:
        st.warning(f"⚠️ Erro ao carregar credenciais Google Sheets do arquivo local '{GSHEETS_CREDENTIALS_PATH_LOCAL}': {e}. Algumas funcionalidades podem ser afetadas.")
else:
    try:
        if "GOOGLE_SHEETS_CREDENTIALS" in st.secrets: 
            base64_encoded_json_sheets = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
            decoded_json_bytes_sheets = base64.b64decode(base64_encoded_json_sheets)
            service_account_info_str_sheets = decoded_json_bytes_sheets.decode('utf-8')
            sheets_credentials_info = json.loads(service_account_info_str_sheets)
            
            sheets_gc = gspread.service_account_from_dict(sheets_credentials_info)
        else:
            st.warning("⚠️ Credenciais 'GOOGLE_SHEETS_CREDENTIALS' não encontradas nos Streamlit Secrets. Algumas funcionalidades podem ser afetadas.")
    except Exception as e:
        st.warning(f"⚠️ Erro inesperado ao carregar credenciais Google Sheets do Streamlit Secrets: {e}. Algumas funcionalidades podem ser afetadas.")

# Verifica se sheets_gc foi inicializado. Se não, mas o BQ está ok, não é FATAL, apenas limita funcionalidades.
if not sheets_gc:
    # Se chegamos aqui, ou as credenciais do sheets não foram encontradas/carregadas, ou deram erro.
    # Não vamos st.stop() aqui, pois o dashboard ainda pode funcionar com dados do BigQuery.
    pass


# --- Constantes de Negócio ---
TAXA_ADWORK_PERCENT = 0.17 # 17% (a taxa percentual em si, usada para cálculo)
DEFAULT_USD_BRL_RATE = 5.00 # Cotação padrão para caso a API falhe
COMISSAO_PERCENT = 0.03 # 3%
FUNDO_RESERVA_PERCENT = 0.10 # 10%


# --- Nomes das Tabelas BigQuery (COM OS CAMINHOS COMPLETOS FORNECIDOS) ---
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


def format_number(value, currency=False, percentage=False, decimal_places=0, x_suffix=False):
    """
    Formata um número para exibição, com opções de moeda, porcentagem ou sufixo 'x'.
    """
    if pd.isna(value) or value is None:
        return "N/A"
    
    # Handle infinite values from numpy or direct float('inf')
    if isinstance(value, float) and (np.isinf(value) or value == float('inf')):
        return "Inf" + ("%" if percentage else "")

    # Formata o valor numérico com casas decimais e separadores brasileiros
    formatted_value = f"{value:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if percentage:
        return formatted_value + "%"
    elif currency:
        return f"R$ {formatted_value}"
    elif x_suffix: # Novo sufixo para ROAS
        return formatted_value + "x"
    else:
        return formatted_value

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
            return None # De 0 para um valor não-zero
    
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
    total_leads_original = df_processed['total_leads'].sum() 
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
    elif total_receita > 0: # Custo zero, mas receita positiva, ROAS/ROI é indefinido
        roi = np.nan
        roas = np.nan
        
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
        with st.spinner("Carregando dados do BigQuery..."): # Mantém spinner para esta operação
            df = query_job.to_dataframe()
            if 'data' in df.columns:
                df['data'] = pd.to_datetime(df['data'])
        return df
    except Exception as e:
        st.error(f"❌ Erro ao executar a consulta BigQuery: {e}")
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
            df_combined['total_receita'] = pd.to_numeric(df_combined['total_receita'], errors='coerce').fillna(0)
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

# --- NOVA FUNÇÃO: Busca nomes de conta do BigQuery ---
@st.cache_data(ttl=3600) # Cache por 1 hora
def get_bigquery_distinct_account_names():
    """
    Busca nomes de conta distintos da tabela campaign_insights do BigQuery.
    Retorna um DataFrame Pandas com a coluna 'account_name'.
    """
    if not client: # Verifica se o cliente BigQuery foi inicializado
        st.error("O cliente BigQuery não foi inicializado. Verifique a configuração de credenciais.")
        return pd.DataFrame()

    query = f"""
        SELECT DISTINCT
            account_name
        FROM
            {CAMPAIGN_INSIGHTS_TABLE}
        WHERE
            account_name IS NOT NULL
    """
    
    try:
        df_bq_accounts = get_data_from_bigquery(query)
        return df_bq_accounts
    except Exception as e:
        st.error(f"❌ Erro ao buscar account_names do BigQuery: {e}")
        return pd.DataFrame()

# --- NOVA FUNÇÃO: Carrega dados das abas 'BM ' do Google Sheets e faz junção com nomes de conta do BigQuery ---
@st.cache_data(ttl=3600) 
def load_manager_sheets_data():
    """
    Carrega e consolida dados de abas 'BM ' de uma planilha do Google Sheets,
    e verifica a existência das Contas de Anúncio no BigQuery.
    Retorna um DataFrame Pandas com os dados consolidados e a flag de existência no BQ.
    """
    if not sheets_gc:
        st.warning("⚠️ O cliente para Google Sheets não foi inicializado. Funções que dependem dele não operarão.")
        return pd.DataFrame()

    try:
        spreadsheet = sheets_gc.open_by_key(GSHEETS_SPREADSHEET_ID) 
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"ERRO: Planilha com ID '{GSHEETS_SPREADSHEET_ID}' (nome: '{GSHEETS_SPREADSHEET_NAME}') não encontrada ou o Service Account não tem acesso.")
        st.error(f"Verifique se a planilha foi compartilhada com o e-mail da Service Account como 'Editor'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro ao abrir a planilha do Google Sheets: {e}")
        return pd.DataFrame()

    all_worksheets = spreadsheet.worksheets()
    all_bm_data = []

    with st.spinner(f"Carregando dados da planilha '{GSHEETS_SPREADSHEET_NAME}'..."):
        for ws in all_worksheets:
            if ws.title.startswith("BM "):
                try:
                    records = ws.get_all_records()
                    if records:
                        df = pd.DataFrame(records)
                        df['BM_Origem'] = ws.title
                        all_bm_data.append(df)
                except Exception as e:
                    st.warning(f"⚠️ Erro ao ler a aba '{ws.title}': {e}. Ignorando esta aba.")

    if not all_bm_data:
        st.warning("Nenhuma aba que começa com 'BM ' foi encontrada ou continha dados na planilha do Google Sheets. Retornando DataFrame vazio para gestores.")
        return pd.DataFrame()

    final_consolidated_df = pd.concat(all_bm_data, ignore_index=True)

    # --- NOVO: Carregar dados de account_name do BigQuery e fazer junção ---
    df_bq_accounts = get_bigquery_distinct_account_names()

    if not df_bq_accounts.empty and 'Conta de Anúncio' in final_consolidated_df.columns:
        final_consolidated_df['Conta de Anúncio_cleaned'] = final_consolidated_df['Conta de Anúncio'].astype(str).str.lower().str.strip()
        df_bq_accounts['account_name_clean'] = df_bq_accounts['account_name'].astype(str).str.lower().str.strip()

        merged_df = pd.merge(
            final_consolidated_df,
            df_bq_accounts[['account_name_clean']].drop_duplicates(), 
            left_on='Conta de Anúncio_cleaned',
            right_on='account_name_clean',
            how='left',
            indicator=True 
        )
        
        merged_df['encontrado_no_bigquery'] = merged_df['_merge'] == 'both'
        merged_df = merged_df.drop(columns=['_merge'], errors='ignore') 
        merged_df = merged_df.drop(columns=['Conta de Anúncio_cleaned'], errors='ignore')
        return merged_df
    elif 'Conta de Anúncio' not in final_consolidated_df.columns:
        st.warning("⚠️ A coluna 'Conta de Anúncio' não foi encontrada nos dados do Google Sheets. A junção com BigQuery não pode ser realizada.")
        return final_consolidated_df
    else:
        st.warning("⚠️ Não foi possível carregar nomes de conta do BigQuery para realizar a junção. Retornando apenas dados do Google Sheets.")
        return final_consolidated_df

# --- NOVO: Função para obter o faturamento total do mês anterior ---
@st.cache_data(ttl=3600)
def get_previous_month_overall_faturamento(current_period_start_date):
    """
    Calcula o faturamento total (receita) para o mês calendário completo
    imediatamente anterior ao current_period_start_date.
    """
    # Calcula as datas para o mês completo anterior
    last_day_of_previous_month = current_period_start_date - timedelta(days=1) 
    start_day_of_previous_month = last_day_of_previous_month.replace(day=1)

    # Carrega os dados de performance para o mês anterior
    df_prev_month_performance = load_data_for_period(start_day_of_previous_month, last_day_of_previous_month)

    if df_prev_month_performance.empty:
        st.warning(f"Nenhum dado encontrado para o mês anterior ({start_day_of_previous_month.strftime('%Y-%m-%d')} a {last_day_of_previous_month.strftime('%Y-%m-%d')}) para calcular o faturamento total.")
        return 0.0 # Retorna 0 se não houver dados para o mês anterior
    
    # Soma a receita total para o mês anterior
    overall_faturamento_prev_month = df_prev_month_performance['total_receita'].sum()
    return overall_faturamento_prev_month


# --- FUNÇÃO PRINCIPAL: Agrega os dados de performance por Gestor ---
@st.cache_data(ttl=3600) 
def get_manager_ranking_data(df_ad_performance_input: pd.DataFrame): 
    """
    Agrega as métricas por gestor para gerar o ranking e retorna também
    o DataFrame de performance diária com a coluna 'Gestor' adicionada.
    df_ad_performance_input: DataFrame com dados de performance já carregados do BigQuery.
    Retorna: (df_ranking, df_daily_performance_with_managers)
    """
    if df_ad_performance_input.empty:
        st.warning("⚠️ DataFrame de performance vazio fornecido para agregação de gestores.")
        return pd.DataFrame(), pd.DataFrame() # Retorna dois DataFrames vazios
    
    # 2. Carregar dados dos gestores do Google Sheets
    df_manager_accounts = load_manager_sheets_data()

    if df_manager_accounts.empty:
        st.warning("⚠️ Nenhum dado de gestores/contas encontrado na planilha do Google Sheets. O ranking de gestores pode estar incompleto.")
        return pd.DataFrame(), pd.DataFrame() # Retorna dois DataFrames vazios

    # Usar os dados de performance de entrada
    merged_df = df_ad_performance_input.copy()

    # Preparar chaves de junção
    df_manager_accounts['Conta de Anúncio_cleaned'] = df_manager_accounts['Conta de Anúncio'].astype(str).str.lower().str.strip()

    # Realizar a junção dos dados de performance com os dados dos gestores
    merged_df = pd.merge(
        merged_df, 
        df_manager_accounts[['BM_Origem', 'Responsável', 'Conta de Anúncio', 'Conta de Anúncio_cleaned']],
        left_on='utm_campaign_norm',
        right_on='Conta de Anúncio_cleaned',
        how='left'
    )
    
    # Preencher gestores não atribuídos explicitamente no sheets
    if 'Responsável' in merged_df.columns:
        merged_df['Gestor'] = merged_df['Responsável'].fillna('Não Atribuído')
    else:
        merged_df['Gestor'] = 'Não Atribuído' # Fallback
    
    # Remover colunas auxiliares de junção e da planilha que não serão mais usadas
    merged_df = merged_df.drop(columns=['Conta de Anúncio_cleaned', 'Responsável', 'BM_Origem', 'Conta de Anúncio'], errors='ignore')

    # Garantir que as colunas numéricas são float para cálculos
    numeric_cols_for_agg = ['total_impressoes', 'total_cliques', 'total_custo', 'total_receita']
    for col in numeric_cols_for_agg:
        if col not in merged_df.columns: 
            merged_df[col] = 0.0
        merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0) # Garante após o merge

    # Calcular Lucro Bruto
    merged_df['Lucro_Bruto'] = merged_df['total_receita'] - merged_df['total_custo']

    # --- Armazenar o DataFrame diário com gestores antes de agrupar ---
    df_daily_performance_with_managers = merged_df.copy()

    # Agrupar por Gestor e calcular métricas agregadas para o ranking
    df_ranking = merged_df.groupby('Gestor').agg(
        Total_Projetos=('utm_campaign_norm', 'nunique'), # <<<<< ADICIONE ESTA LINHA
        Total_Faturamento=('total_receita', 'sum'),
        Total_Custo=('total_custo', 'sum'),
        Lucro_Bruto=('Lucro_Bruto', 'sum'), 
        Total_Impressoes=('total_impressoes', 'sum'),
        Total_Cliques=('total_cliques', 'sum'),
    ).reset_index()

    # Calcular ROI e ROAS após a agregação
    df_ranking['ROI_Percentual'] = (df_ranking['Lucro_Bruto'] / df_ranking['Total_Custo'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
    df_ranking['ROAS'] = (df_ranking['Total_Faturamento'] / df_ranking['Total_Custo']).replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Calcular Comissao, Fundo Reserva, Lucro Liquido Final para cada gestor
    df_ranking['Comissao'] = df_ranking['Total_Faturamento'] * COMISSAO_PERCENT
    df_ranking['Fundo_Reserva'] = df_ranking['Lucro_Bruto'] * FUNDO_RESERVA_PERCENT
    df_ranking['Lucro_Liquido_Final'] = df_ranking['Lucro_Bruto'] - df_ranking['Comissao'] - df_ranking['Fundo_Reserva']

    return df_ranking, df_daily_performance_with_managers

# Em utils.py

# ... (Mantenha todas as importações e funções existentes) ...

def get_project_ranking_data(df):
    """
    Agrupa os dados por projeto e gestor, calculando as métricas financeiras.
    Retorna um DataFrame com o ranking dos projetos.
    """
    # Assegura que as colunas essenciais para o agrupamento e cálculo existam
    required_cols = ['Gestor', 'utm_campaign_norm', 'total_receita', 'total_custo']
    for col in required_cols:
        if col not in df.columns:
            # Em um ambiente de produção, você pode querer um tratamento de erro mais sofisticado
            st.error(f"Erro: Coluna '{col}' não encontrada no DataFrame para ranking de projetos. Verifique sua função de carregamento de dados.")
            return pd.DataFrame() # Retorna um DataFrame vazio para evitar quebrar o app

    # Agrega as métricas base por Projeto (utm_campaign_norm) e Gestor
    df_agg = df.groupby(['utm_campaign_norm', 'Gestor']).agg(
        Total_Receita=('total_receita', 'sum'),
        Total_Custo=('total_custo', 'sum')
    ).reset_index()

    # Calcula as métricas derivadas APÓS a agregação para garantir a correção dos totais
    df_agg['Lucro_Bruto'] = df_agg['Total_Receita'] - df_agg['Total_Custo']
    df_agg['Comissao'] = df_agg['Total_Receita'] * COMISSAO_PERCENT # Usa a constante de comissão
    
    # Supondo que FUNDO_RESERVA_PERCENT se aplica ao lucro bruto antes da comissão em nível de projeto
    # Ajuste esta lógica se a aplicação do fundo de reserva for diferente (e.g., sobre lucro líquido)
    df_agg['Lucro_Liquido_Final'] = df_agg['Lucro_Bruto'] - df_agg['Comissao'] - (df_agg['Lucro_Bruto'] * FUNDO_RESERVA_PERCENT)

    # Recalcula o ROI (Retorno sobre Investimento) baseado nos valores agregados
    df_agg['ROI_Percentual'] = (
        (df_agg['Lucro_Bruto'] / df_agg['Total_Custo']) * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0) # Trata divisão por zero, substituindo por 0 ou NaN

    # Renomeia colunas para o display final
    df_agg = df_agg.rename(columns={
        'utm_campaign_norm': 'Projeto',
        'Total_Custo': 'Investimento',
        'Total_Receita': 'Receita'
    })
    
    # Seleciona e reordena as colunas para a saída final
    final_cols = ['Projeto', 'Gestor', 'Investimento', 'Receita', 'Lucro_Bruto', 'Comissao', 'Lucro_Liquido_Final', 'ROI_Percentual']
    return df_agg[final_cols]

