# pages/2_Faturamento_Por_Site.py
import streamlit as st
import pandas as pd
import datetime
import numpy as np
from utils import (
    format_number, calculate_percentage_delta, calculate_business_metrics,
    load_data_for_period, TAXA_ADWORK_PERCENT, get_usd_to_brl_rate
)

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Mídia - Gerenciamento de Sites")

st.title("Gerenciamento de Sites")

# --- FILTROS NO CORPO DA PÁGINA ---
col_date_start, col_date_end, col_domain_filter, col_network_code_filter = st.columns([1, 1, 1.5, 1.5])

with col_date_start:
    today = datetime.date.today()
    default_start_date = today - datetime.timedelta(days=30)
    start_date = st.date_input(
        "Data de Início:",
        value=default_start_date,
        max_value=today,
        key='start_date_site'
    )

with col_date_end:
    end_date = st.date_input(
        "Data de Fim:",
        value=today,
        max_value=today,
        key='end_date_site'
    )

if start_date > end_date:
    st.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

# --- Cálculo do período anterior ---
duration = (end_date - start_date).days + 1
prev_start_date = start_date - datetime.timedelta(days=duration)
prev_end_date = end_date - datetime.timedelta(days=duration)

# Carrega os dados BRUTOS (sem filtro de domínio ainda) para o período atual e anterior
df_raw_current = load_data_for_period(start_date, end_date)
df_raw_previous = load_data_for_period(prev_start_date, prev_end_date)

# --- Filtro de Domínio (Agora na mesma linha das datas) ---
with col_domain_filter:
    st.write("Filtrar por Domínio (Admanager)")

    multiselect_key = 'ms_domains_site'
    checkbox_key = 'cb_all_domains_site'

    available_domains_list = list(df_raw_current[
        (df_raw_current['source'] == 'Admanager (UTM)') | (df_raw_current['source'] == 'Admanager (UTM) & Meta Ads') & (df_raw_current['dominio'].notna())
    ]['dominio'].unique())
    available_domains_list.sort()

    if multiselect_key not in st.session_state:
        st.session_state[multiselect_key] = available_domains_list

    current_selected_valid = [d for d in st.session_state[multiselect_key] if d in available_domains_list]
    if set(current_selected_valid) != set(st.session_state[multiselect_key]):
        st.session_state[multiselect_key] = current_selected_valid
    
    def on_checkbox_change_site():
        if st.session_state[checkbox_key]:
            st.session_state[multiselect_key] = available_domains_list
        else:
            st.session_state[multiselect_key] = []

    initial_checkbox_value = (set(st.session_state[multiselect_key]) == set(available_domains_list) and len(available_domains_list) > 0)
    
    st.checkbox(
        "Selecionar Todos",
        value=initial_checkbox_value,
        key=checkbox_key,
        on_change=on_checkbox_change_site
    )

    def on_multiselect_change_site():
        if set(st.session_state[multiselect_key]) == set(available_domains_list) and len(available_domains_list) > 0:
            st.session_state[checkbox_key] = True
        else:
            st.session_state[checkbox_key] = False

    selected_domains = st.multiselect(
        "Selecione os domínios:",
        options=available_domains_list,
        key=multiselect_key,
        label_visibility="collapsed",
        on_change=on_multiselect_change_site
    )
    if not available_domains_list:
        selected_domains = []

# Adição do filtro de Network Code
with col_network_code_filter:
    st.write("Filtrar por Network Code (Admanager)")

    multiselect_key_nc = 'ms_network_code_site'
    checkbox_key_nc = 'cb_all_network_code_site'

    available_network_codes_list = list(df_raw_current[
        ((df_raw_current['source'] == 'Admanager (UTM)') | (df_raw_current['source'] == 'Admanager (UTM) & Meta Ads')) & (df_raw_current['network_code'].notna())
    ]['network_code'].unique())
    available_network_codes_list.sort()

    if multiselect_key_nc not in st.session_state:
        st.session_state[multiselect_key_nc] = available_network_codes_list

    current_selected_valid_nc = [nc for nc in st.session_state[multiselect_key_nc] if nc in available_network_codes_list]
    if set(current_selected_valid_nc) != set(st.session_state[multiselect_key_nc]):
        st.session_state[multiselect_key_nc] = current_selected_valid_nc

    def on_checkbox_change_network_code_site():
        if st.session_state[checkbox_key_nc]:
            st.session_state[multiselect_key_nc] = available_network_codes_list
        else:
            st.session_state[multiselect_key_nc] = []

    def on_multiselect_change_network_code_site():
        if set(st.session_state[multiselect_key_nc]) == set(available_network_codes_list) and len(available_network_codes_list) > 0:
            st.session_state[checkbox_key_nc] = True
        else:
            st.session_state[checkbox_key_nc] = False

    initial_checkbox_value_nc = (set(st.session_state[multiselect_key_nc]) == set(available_network_codes_list) and len(available_network_codes_list) > 0)

    st.checkbox(
        "Selecionar Todos",
        value=initial_checkbox_value_nc,
        key=checkbox_key_nc,
        on_change=on_checkbox_change_network_code_site
    )

    selected_network_codes = st.multiselect(
        "Selecione os Network Codes:",
        options=available_network_codes_list,
        key=multiselect_key_nc,
        label_visibility="collapsed",
        on_change=on_multiselect_change_network_code_site
    )
    if not available_network_codes_list:
        selected_network_codes = []

# Lógica de aplicação dos filtros
df_data_current_filtered = df_raw_current.copy()
df_data_previous_filtered = df_raw_previous.copy()

is_admanager_current = (df_data_current_filtered['source'] == 'Admanager (UTM)') | (df_data_current_filtered['source'] == 'Admanager (UTM) & Meta Ads')
is_admanager_previous = (df_data_previous_filtered['source'] == 'Admanager (UTM)') | (df_data_previous_filtered['source'] == 'Admanager (UTM) & Meta Ads')

if selected_domains:
    domain_filter_current = df_data_current_filtered['dominio'].isin(selected_domains)
    domain_filter_previous = df_data_previous_filtered['dominio'].isin(selected_domains)
    is_admanager_current = is_admanager_current & domain_filter_current
    is_admanager_previous = is_admanager_previous & domain_filter_previous
else:
    st.warning("Nenhum domínio do Admanager selecionado. Os dados de Admanager (UTM) e combinados não serão exibidos.")
    is_admanager_current = False
    is_admanager_previous = False

if selected_network_codes:
    network_filter_current = df_data_current_filtered['network_code'].isin(selected_network_codes)
    network_filter_previous = df_data_previous_filtered['network_code'].isin(selected_network_codes)
    is_admanager_current = is_admanager_current & network_filter_current
    is_admanager_previous = is_admanager_previous & network_filter_previous
else:
    if selected_domains:
         st.warning("Nenhum Network Code do Admanager selecionado. Os dados de Admanager (UTM) e combinados não serão exibidos.")
    is_admanager_current = False
    is_admanager_previous = False

df_data_current_filtered = df_data_current_filtered[
    (~ ((df_data_current_filtered['source'] == 'Admanager (UTM)') | (df_data_current_filtered['source'] == 'Admanager (UTM) & Meta Ads'))) | is_admanager_current
].copy()
df_data_previous_filtered = df_data_previous_filtered[
    (~ ((df_data_previous_filtered['source'] == 'Admanager (UTM)') | (df_data_previous_filtered['source'] == 'Admanager (UTM) & Meta Ads'))) | is_admanager_previous
].copy()


st.markdown("--- ")

if df_data_current_filtered.empty and df_data_previous_filtered.empty:
    st.warning("Nenhum dado encontrado para o período selecionado e/ou domínios filtrados. Ajuste os filtros ou verifique as fontes de dados.")
    st.stop()

current_metrics = calculate_business_metrics(df_data_current_filtered)
previous_metrics = calculate_business_metrics(df_data_previous_filtered)

usd_to_brl_rate = get_usd_to_brl_rate()

current_total_revenue_usd = current_metrics['total_receita'] / usd_to_brl_rate if usd_to_brl_rate != 0 else 0
previous_total_revenue_usd = previous_metrics['total_receita'] / usd_to_brl_rate if usd_to_brl_rate != 0 else 0


# --- Big Numbers (Visão Geral) ---
st.subheader("Métricas Gerais do Período")
col_nl, col_roi, col_roas, col_receita_usd, col_receita_brl = st.columns(5)

with col_nl:
    delta = calculate_percentage_delta(current_metrics['lucro_liquido'], previous_metrics['lucro_liquido'])
    st.metric(
        label="Lucro Líquido",
        value=format_number(current_metrics['lucro_liquido'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_roi:
    delta = calculate_percentage_delta(current_metrics['roi'], previous_metrics['roi'])
    st.metric(
        label="ROI",
        value=format_number(current_metrics['roi'], percentage=True, decimal_places=2),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_roas:
    delta = calculate_percentage_delta(current_metrics['roas'], previous_metrics['roas'])
    st.metric(
        label="ROAS",
        value=format_number(current_metrics['roas'], decimal_places=2),
        delta=f"{delta:,.2f}" if delta is not None else None,
        delta_color="normal"
    )
with col_receita_usd:
    delta = calculate_percentage_delta(current_total_revenue_usd, previous_total_revenue_usd)
    st.metric(
        label="Receita Total (USD)",
        value=f"${current_total_revenue_usd:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_receita_brl:
    delta = calculate_percentage_delta(current_metrics['total_receita'], previous_metrics['total_receita'])
    st.metric(
        label="Receita Total (BRL)",
        value=format_number(current_metrics['total_receita'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )

st.markdown("---")

# --- ESTATÍSTICAS ADMANAGER ---
st.subheader("Estatísticas Admanager")

df_admanager_current = df_data_current_filtered[
    (df_data_current_filtered['source'].str.contains('Admanager')) &
    (df_data_current_filtered['dominio'].notna())
].copy()
df_admanager_previous = df_data_previous_filtered[
    (df_data_previous_filtered['source'].str.contains('Admanager')) &
    (df_data_previous_filtered['dominio'].notna())
].copy()

admanager_current_revenue_brl = df_admanager_current['total_receita'].sum()
admanager_current_impressions = df_admanager_current['total_impressoes'].sum()
admanager_current_clicks = df_admanager_current['total_cliques'].sum()

admanager_previous_revenue_brl = df_admanager_previous['total_receita'].sum()
admanager_previous_impressions = df_admanager_previous['total_impressoes'].sum()
admanager_previous_clicks = df_admanager_previous['total_cliques'].sum()

admanager_current_revenue_usd = admanager_current_revenue_brl / usd_to_brl_rate if usd_to_brl_rate else 0
admanager_previous_revenue_usd = admanager_previous_revenue_brl / usd_to_brl_rate if usd_to_brl_rate else 0

admanager_current_ecpm = (admanager_current_revenue_usd / admanager_current_impressions * 1000) if admanager_current_impressions else 0
admanager_previous_ecpm = (admanager_previous_revenue_usd / admanager_previous_impressions * 1000) if admanager_previous_impressions else 0


col_usd, col_brl, col_imp, col_ecpm, col_cli = st.columns(5)

with col_usd:
    delta = calculate_percentage_delta(admanager_current_revenue_usd, admanager_previous_revenue_usd)
    st.metric(
        label="Ganhos (USD)",
        value=f"${admanager_current_revenue_usd:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_brl:
    delta = calculate_percentage_delta(admanager_current_revenue_brl, admanager_previous_revenue_brl)
    st.metric(
        label="Ganhos (BRL)",
        value=format_number(admanager_current_revenue_brl, currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_imp:
    delta = calculate_percentage_delta(admanager_current_impressions, admanager_previous_impressions)
    st.metric(
        label="Impressões",
        value=format_number(admanager_current_impressions),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_ecpm:
    delta = calculate_percentage_delta(admanager_current_ecpm, admanager_previous_ecpm)
    st.metric(
        label="eCPM (USD)",
        value=f"${admanager_current_ecpm:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_cli:
    delta = calculate_percentage_delta(admanager_current_clicks, admanager_previous_clicks)
    st.metric(
        label="Cliques",
        value=format_number(admanager_current_clicks),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )

st.markdown("---")

# --- ESTATÍSTICAS META ADS ---
st.subheader("Estatísticas Meta Ads")

df_meta_ads_current = df_data_current_filtered[df_data_current_filtered['source'] == 'Meta Ads'].copy()
df_meta_ads_previous = df_data_previous_filtered[df_data_previous_filtered['source'] == 'Meta Ads'].copy()

meta_ads_current_cost = df_meta_ads_current['total_custo'].sum()
meta_ads_current_leads = df_meta_ads_current['total_leads'].sum() + df_meta_ads_current['total_mensagens'].sum()
meta_ads_current_impressions = df_meta_ads_current['total_impressoes'].sum()
meta_ads_current_clicks = df_meta_ads_current['total_cliques'].sum()

meta_ads_previous_cost = df_meta_ads_previous['total_custo'].sum()
meta_ads_previous_leads = df_meta_ads_previous['total_leads'].sum() + df_meta_ads_previous['total_mensagens'].sum()
meta_ads_previous_impressions = df_meta_ads_previous['total_impressoes'].sum()
meta_ads_previous_clicks = df_meta_ads_previous['total_cliques'].sum()

meta_ads_current_cpl = meta_ads_current_cost / meta_ads_current_leads if meta_ads_current_leads else 0
meta_ads_current_ctr = (meta_ads_current_clicks / meta_ads_current_impressions * 100) if meta_ads_current_impressions else 0
meta_ads_current_cpm = (meta_ads_current_cost / meta_ads_current_impressions * 1000) if meta_ads_current_impressions else 0
meta_ads_current_cpc = meta_ads_current_cost / meta_ads_current_clicks if meta_ads_current_clicks else 0

meta_ads_previous_cpl = meta_ads_previous_cost / meta_ads_previous_leads if meta_ads_previous_leads else 0
meta_ads_previous_ctr = (meta_ads_previous_clicks / meta_ads_previous_impressions * 100) if meta_ads_previous_impressions else 0
meta_ads_previous_cpm = (meta_ads_previous_cost / meta_ads_previous_impressions * 1000) if meta_ads_previous_impressions else 0
meta_ads_previous_cpc = meta_ads_previous_cost / meta_ads_previous_clicks if meta_ads_previous_clicks else 0


col_gasto, col_leads, col_cpl, col_imp_meta, col_cli_meta = st.columns(5)
col_ctr, col_cpm, col_cpc = st.columns(3)

with col_gasto:
    delta = calculate_percentage_delta(meta_ads_current_cost, meta_ads_previous_cost)
    st.metric(
        label="Gasto",
        value=format_number(meta_ads_current_cost, currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )
with col_leads:
    delta = calculate_percentage_delta(meta_ads_current_leads, meta_ads_previous_leads)
    st.metric(
        label="Leads + Mensagens",
        value=format_number(meta_ads_current_leads),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_cpl:
    delta = calculate_percentage_delta(meta_ads_current_cpl, meta_ads_previous_cpl)
    st.metric(
        label="CPL (Leads+Msg)",
        value=format_number(meta_ads_current_cpl, currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )
with col_imp_meta:
    delta = calculate_percentage_delta(meta_ads_current_impressions, meta_ads_previous_impressions)
    st.metric(
        label="Impressões",
        value=format_number(meta_ads_current_impressions),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_cli_meta:
    delta = calculate_percentage_delta(meta_ads_current_clicks, meta_ads_previous_clicks)
    st.metric(
        label="Cliques",
        value=format_number(meta_ads_current_clicks),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )

with col_ctr:
    delta = calculate_percentage_delta(meta_ads_current_ctr, meta_ads_previous_ctr)
    st.metric(
        label="CTR",
        value=format_number(meta_ads_current_ctr, percentage=True, decimal_places=2),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_cpm:
    delta = calculate_percentage_delta(meta_ads_current_cpm, meta_ads_previous_cpm)
    st.metric(
        label="CPM",
        value=format_number(meta_ads_current_cpm, currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )
with col_cpc:
    delta = calculate_percentage_delta(meta_ads_current_cpc, meta_ads_previous_cpc)
    st.metric(
        label="CPC",
        value=format_number(meta_ads_current_cpc, currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )

st.markdown("---")

# --- TABELA: FATURAMENTO POR SITE ---
st.subheader("Visão Detalhada por Site")

df_admanager_domains = df_data_current_filtered[
    (df_data_current_filtered['source'].str.contains('Admanager')) & (df_data_current_filtered['dominio'].notna())
].copy()

if not df_admanager_domains.empty:
    df_admanager_domains['total_receita'] = df_admanager_domains['total_receita'].fillna(0).astype(float)
    df_admanager_domains['total_custo'] = df_admanager_domains['total_custo'].fillna(0).astype(float)

    df_domain_summary = df_admanager_domains.groupby('dominio').agg(
        total_receita=('total_receita', 'sum'),
        total_custo=('total_custo', 'sum')
    ).reset_index()

    total_revenue_domains = df_domain_summary['total_receita'].sum()
    st.markdown(f"**Faturamento Bruto (Sites Selecionados):** {format_number(total_revenue_domains, currency=True)}")

    df_domain_summary['custo_taxa_adwork'] = df_domain_summary['total_receita'] * TAXA_ADWORK_PERCENT
    df_domain_summary['receita_liquida'] = df_domain_summary['total_receita'] - df_domain_summary['total_custo'] - df_domain_summary['custo_taxa_adwork']

    def calculate_roi_domain(row):
        if row['total_custo'] == 0:
            return 0 if row['total_receita'] == 0 else float('inf')
        return ((row['total_receita'] - row['total_custo']) / row['total_custo']) * 100

    def calculate_roas_domain(row):
        if row['total_custo'] == 0:
            return 0 if row['total_receita'] == 0 else float('inf')
        return row['total_receita'] / row['total_custo']

    df_domain_summary['roi'] = df_domain_summary.apply(calculate_roi_domain, axis=1)
    df_domain_summary['roas'] = df_domain_summary.apply(calculate_roas_domain, axis=1)

    total_revenue_overall_domains = df_domain_summary['total_receita'].sum()
    df_domain_summary['participacao'] = (df_domain_summary['total_receita'] / total_revenue_overall_domains * 100).fillna(0) if total_revenue_overall_domains != 0 else 0

    df_display = df_domain_summary[[
        'dominio', 'total_receita', 'total_custo',
        'receita_liquida', 'roi', 'roas', 'participacao'
    ]].copy()

    df_display.rename(columns={
        'dominio': 'NOME',
        'total_receita': 'RECEITA (BRL)',
        'total_custo': 'GASTO (BRL)',
        'receita_liquida': 'RECEITA LÍQUIDA (BRL)',
        'roi': 'ROI (%)',
        'roas': 'ROAS',
        'participacao': 'PARTICIPAÇÃO (%)'
    }, inplace=True)

    df_display['RECEITA (BRL)'] = df_display['RECEITA (BRL)'].apply(lambda x: format_number(x, currency=True))
    df_display['GASTO (BRL)'] = df_display['GASTO (BRL)'].apply(lambda x: format_number(x, currency=True))
    df_display['RECEITA LÍQUIDA (BRL)'] = df_display['RECEITA LÍQUIDA (BRL)'].apply(lambda x: format_number(x, currency=True))
    
    df_display['ROI (%)'] = df_display['ROI (%)'].apply(lambda x: format_number(x, percentage=True, decimal_places=2))
    df_display['ROAS'] = df_display['ROAS'].apply(lambda x: format_number(x, decimal_places=2))
    df_display['PARTICIPAÇÃO (%)'] = df_display['PARTICIPAÇÃO (%)'].apply(lambda x: format_number(x, percentage=True, decimal_places=2))

    df_display['AÇÕES'] = 'Abrir Blog'

    def color_metrics(val, is_currency=False):
        if isinstance(val, str) and ("Inf" in val or "N/A" in val):
            return ''
        
        clean_val = val.replace('R$', '').replace('.', '').replace(',', '.') if is_currency else val
        try:
            num_val = float(clean_val.replace('%', ''))
        except (ValueError, TypeError):
            return ''
        
        if num_val > 0:
            return 'color: green'
        elif num_val < 0:
            return 'color: red'
        return ''

    def apply_row_colors(row):
        styles = [''] * len(row)
        if 'RECEITA LÍQUIDA (BRL)' in row.index:
            styles[row.index.get_loc('RECEITA LÍQUIDA (BRL)')] = color_metrics(row['RECEITA LÍQUIDA (BRL)'], is_currency=True)
        if 'ROI (%)' in row.index:
            styles[row.index.get_loc('ROI (%)')] = color_metrics(row['ROI (%)'], is_currency=False)
        return styles

    st.dataframe(df_display.style.apply(apply_row_colors, axis=1), hide_index=True, use_container_width=True)

    if df_domain_summary['total_custo'].sum() == 0 and not df_domain_summary.empty:
        st.info("Nota: 'GASTO (BRL)' para sites do Admanager é exibido como zero, pois os custos não estão associados diretamente aos domínios na consulta atual do BigQuery. Ajustes na fonte de dados ou na query podem ser necessários para incluir custos por domínio.")

else:
    st.info("Nenhum dado do Admanager com domínio encontrado para o período selecionado ou filtrado para esta tabela.")

st.markdown("---")
st.subheader("Dados Brutos (Período Atual)")

if not df_data_current_filtered.empty:
    df_display_raw = df_data_current_filtered.copy()

    # --- Pre-processing for calculations ---
    # Garante que as colunas numéricas são float e trata NaNs para cálculo
    numeric_for_calc_cols = ['total_receita', 'total_custo', 'total_impressoes', 'total_cliques', 'total_leads', 'total_mensagens']
    for col in numeric_for_calc_cols:
        if col in df_display_raw.columns:
            df_display_raw[col] = pd.to_numeric(df_display_raw[col], errors='coerce').fillna(0)
        else:
            df_display_raw[col] = 0.0 # Garante que a coluna exista com 0 se estiver faltando

    # Calcula lucro e ROI por linha ANTES de dropar/renomear colunas
    df_display_raw['custo_taxa_adwork'] = df_display_raw['total_receita'] * TAXA_ADWORK_PERCENT
    df_display_raw['lucro_liquido'] = df_display_raw['total_receita'] - df_display_raw['total_custo'] - df_display_raw['custo_taxa_adwork']
    
    def calculate_roi_for_raw_row(row):
        receita = row['total_receita']
        custo = row['total_custo']
        if custo == 0:
            return 0 if receita == 0 else np.inf # Usar np.inf para valores infinitos
        return ((receita - custo) / custo) * 100
    df_display_raw['roi'] = df_display_raw.apply(calculate_roi_for_raw_row, axis=1)

    # 1. Retirar a coluna de source (a original que indica 'Admanager (UTM)', 'Meta Ads')
    if 'source' in df_display_raw.columns:
        df_display_raw = df_display_raw.drop(columns=['source'])

    # 2. Combinar 'total_leads' e 'total_mensagens' em uma coluna só
    combined_leads_messages = pd.Series([0.0] * len(df_display_raw), index=df_display_raw.index)
    if 'total_leads' in df_display_raw.columns:
        combined_leads_messages += df_display_raw['total_leads']
    if 'total_mensagens' in df_display_raw.columns:
        combined_leads_messages += df_display_raw['total_mensagens']
    df_display_raw['Leads + Mensagens'] = combined_leads_messages

    # Dropar as colunas originais de leads e mensagens e a coluna auxiliar de custo de taxa
    cols_to_drop_if_exist = ['total_leads', 'total_mensagens', 'custo_taxa_adwork']
    df_display_raw = df_display_raw.drop(columns=[col for col in cols_to_drop_if_exist if col in df_display_raw.columns])

    # 3. Renomear colunas: remover "total_" e simplificar UTMs
    column_renames = {}
    for col in df_display_raw.columns:
        if col.startswith('total_'):
            column_renames[col] = col.replace('total_', '')
        elif col.startswith('utm_'):
            if col == 'utm_campaign_norm':
                column_renames[col] = 'Campaign' # Nome mais simples
            elif col == 'utm_source':
                column_renames[col] = 'Source' # Nome mais simples
            # Outras colunas utm_ serão descartadas por não estarem na ordem final
    df_display_raw = df_display_raw.rename(columns=column_renames)

    # 4. Reordenar colunas
    prefix_cols = ['data', 'pais', 'dominio']
    network_code_col = 'network_code'
    
    # UTMs atualizadas (apenas Campaign e Source)
    utm_cols_display_names = ['Campaign', 'Source']
    
    # Novas métricas incluindo lucro e ROI
    metric_cols_display_names = [
        'custo', 'receita', 'lucro_liquido', 'roi', # Usando as renomeadas e recém-calculadas
        'impressoes', 'cliques', 'Leads + Mensagens' # Usando as renomeadas/combinadas
    ]

    final_column_order = []
    for col in prefix_cols:
        if col in df_display_raw.columns:
            final_column_order.append(col)

    if network_code_col in df_display_raw.columns:
        final_column_order.append(network_code_col)
    
    for col in utm_cols_display_names:
        if col in df_display_raw.columns:
            final_column_order.append(col)
            
    # Inserir Lucro Líquido e ROI na ordem desejada
    if 'lucro_liquido' in df_display_raw.columns:
        final_column_order.append('lucro_liquido')
    if 'roi' in df_display_raw.columns:
        final_column_order.append('roi')

    # Adicionar as demais colunas de métricas
    for col in [m for m in metric_cols_display_names if m not in ['lucro_liquido', 'roi']]: # Evitar duplicidade
        if col in df_display_raw.columns:
            final_column_order.append(col)

    # Filtrar para garantir que apenas colunas existentes no DataFrame estejam na ordem final
    final_column_order_filtered = [col for col in final_column_order if col in df_display_raw.columns]
    df_display_raw = df_display_raw[final_column_order_filtered]

    # --- Styling (Heatmap e Formatação) ---
    columns_to_heatmap = [
        'custo', 'receita', 'lucro_liquido', 'roi',
        'impressoes', 'cliques', 'Leads + Mensagens'
    ]
    columns_to_heatmap_filtered = [col for col in columns_to_heatmap if col in df_display_raw.columns]

    # Preparar DataFrame para styling (garantindo que os valores são numéricos para o gradient)
    df_numeric_for_styling = df_display_raw.copy()
    for col in columns_to_heatmap_filtered:
        df_numeric_for_styling[col] = pd.to_numeric(df_numeric_for_styling[col], errors='coerce')
        # Substituir inf por NaN para que não sejam coloridos e não distorçam a escala do gradient
        df_numeric_for_styling[col] = df_numeric_for_styling[col].replace([np.inf, -np.inf], np.nan) 
    
    styled_df = df_numeric_for_styling.style

    # Definir opções de formatação para cada coluna
    cols_to_format_dict = {
        'custo': {'currency': True},
        'receita': {'currency': True},
        'lucro_liquido': {'currency': True},
        'roi': {'percentage': True, 'decimal_places': 2},
        'impressoes': {'decimal_places': 0},
        'cliques': {'decimal_places': 0},
        'Leads + Mensagens': {'decimal_places': 0}
    }

    for col in columns_to_heatmap_filtered:
        # Aplicar background_gradient para as colunas numéricas válidas
        # Evitar aplicar gradient se todos os valores forem NaN ou iguais
        min_val = df_numeric_for_styling[col].min()
        max_val = df_numeric_for_styling[col].max()
        if pd.notna(min_val) and pd.notna(max_val) and min_val != max_val:
            styled_df = styled_df.background_gradient(cmap='YlGn', subset=[col])
        
        # Aplicar formatação usando a função format_number
        format_options = cols_to_format_dict.get(col, {})
        # Usamos uma lambda para aplicar format_number mantendo os argumentos
        styled_df = styled_df.format({col: lambda x, opts=format_options: format_number(x, **opts)})

    st.dataframe(styled_df, hide_index=True, use_container_width=True)
else:
    st.info("Nenhum dado bruto encontrado para o período atual após a filtragem.")