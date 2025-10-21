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
col_date_start, col_date_end, col_domain_filter = st.columns([1, 1, 2]) # Ajusta as larguras das colunas

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
with col_domain_filter: # O filtro de domínio será renderizado nesta terceira coluna
    st.write("Filtrar por Domínio (Admanager)") # Título para a seção de domínio

    # Chaves únicas para os componentes nesta página
    multiselect_key = 'ms_domains_site'
    checkbox_key = 'cb_all_domains_site'

    # Lista de domínios disponíveis (sempre como lista)
    available_domains_list = list(df_raw_current[
        (df_raw_current['source'] == 'Admanager') & (df_raw_current['dominio'].notna())
    ]['dominio'].unique())
    available_domains_list.sort() # Garante ordenação consistente

    # --- Lógica de Sincronização Checkbox <-> Multiselect usando Session State ---

    # 1. Inicializa o estado do multiselect na session_state, se ainda não existir
    if multiselect_key not in st.session_state:
        st.session_state[multiselect_key] = available_domains_list # Por padrão, inicia com todos selecionados

    # 2. Garante que os domínios selecionados ainda são válidos após uma mudança nos available_domains (ex: mudança de data)
    current_selected_valid = [d for d in st.session_state[multiselect_key] if d in available_domains_list]
    if set(current_selected_valid) != set(st.session_state[multiselect_key]):
        st.session_state[multiselect_key] = current_selected_valid
    
    # 3. Define a função de callback para o checkbox
    def on_checkbox_change_site():
        if st.session_state[checkbox_key]:
            st.session_state[multiselect_key] = available_domains_list
        else:
            st.session_state[multiselect_key] = []

    # 4. Define a função de callback para o multiselect
    def on_multiselect_change_site():
        # Se todos os domínios disponíveis estão selecionados no multiselect, marca o checkbox
        if set(st.session_state[multiselect_key]) == set(available_domains_list) and len(available_domains_list) > 0:
            st.session_state[checkbox_key] = True
        else:
            st.session_state[checkbox_key] = False

    # 5. Renderiza o checkbox
    # O valor inicial do checkbox reflete se todos os domínios estão atualmente selecionados no multiselect
    initial_checkbox_value = (set(st.session_state[multiselect_key]) == set(available_domains_list) and len(available_domains_list) > 0)
    
    select_all_domains_widget = st.checkbox(
        "Selecionar Todos",
        value=initial_checkbox_value, # Valor inicial baseado no estado do multiselect
        key=checkbox_key, # Chave única para o checkbox
        on_change=on_checkbox_change_site # Ativado quando o checkbox é clicado
    )

    # 6. Renderiza o multiselect
    # Seu valor é controlado diretamente por st.session_state[multiselect_key]
    selected_domains = st.multiselect(
        "Selecione os domínios:",
        options=available_domains_list,
        key=multiselect_key, # Chave única para o multiselect
        label_visibility="collapsed",
        on_change=on_multiselect_change_site # Ativado quando a seleção no multiselect muda
    )
    # Se não há domínios disponíveis, garante que selected_domains esteja vazio
    if not available_domains_list:
        selected_domains = []

# Aplicar filtro de domínio aos DataFrames
if selected_domains:
    df_data_current_filtered = df_raw_current[
        (df_raw_current['dominio'].isin(selected_domains)) |
        (df_raw_current['source'] != 'Admanager')
    ].copy()
    df_data_previous_filtered = df_raw_previous[
        (df_raw_previous['dominio'].isin(selected_domains)) |
        (df_raw_previous['source'] != 'Admanager')
    ].copy()
else:
    st.warning("Nenhum domínio do Admanager selecionado. Exibindo apenas dados de outras fontes.")
    df_data_current_filtered = df_raw_current[df_raw_current['source'] != 'Admanager'].copy()
    df_data_previous_filtered = df_raw_previous[df_raw_previous['source'] != 'Admanager'].copy()

st.markdown("--- ") # Separador para o conteúdo principal

if df_data_current_filtered.empty and df_data_previous_filtered.empty:
    st.warning("Nenhum dado encontrado para o período selecionado e/ou domínios filtrados. Ajuste os filtros ou verifique as fontes de dados.")
    st.stop()

# Calcula todas as métricas para os períodos FILTRADOS (Visão Geral)
current_metrics = calculate_business_metrics(df_data_current_filtered)
previous_metrics = calculate_business_metrics(df_data_previous_filtered)

# ... (Resto do código da página 2_Faturamento_Por_Site.py permanece o mesmo)
# (Big Numbers, Estatísticas Admanager, Estatísticas Meta Ads, Tabela Detalhada)
# ...

# --- Big Numbers (Visão Geral) ---
st.subheader("Visão Geral")
col_nl, col_roi, col_roas, col_taxa = st.columns(4)

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
        value=format_number(current_metrics['roas'], percentage=True, decimal_places=2),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_taxa:
    delta = calculate_percentage_delta(current_metrics['custo_taxa_adwork'], previous_metrics['custo_taxa_adwork'])
    st.metric(
        label="Custo da Taxa de Adwork",
        value=format_number(current_metrics['custo_taxa_adwork'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )

st.markdown("---")

# --- ESTATÍSTICAS ADMANAGER ---
st.subheader("Estatísticas Admanager")

# Filtrar apenas os dados do Admanager para o período atual
df_admanager_current = df_data_current_filtered[df_data_current_filtered['source'] == 'Admanager'].copy()
df_admanager_previous = df_data_previous_filtered[df_data_previous_filtered['source'] == 'Admanager'].copy()

# Obter a cotação USD-BRL (a função já é cacheada e lida com erros)
usd_to_brl_rate = get_usd_to_brl_rate()

# Calcular métricas do Admanager para o período atual
admanager_current_revenue_brl = df_admanager_current['total_receita'].sum() # Já está em BRL
admanager_current_impressions = df_admanager_current['total_impressoes'].sum()
admanager_current_clicks = df_admanager_current['total_cliques'].sum()

# Calcular métricas do Admanager para o período anterior
admanager_previous_revenue_brl = df_admanager_previous['total_receita'].sum()
admanager_previous_impressions = df_admanager_previous['total_impressoes'].sum()
admanager_previous_clicks = df_admanager_previous['total_cliques'].sum()

# Ganhos em Dólar (calculado a partir dos ganhos em BRL e da cotação)
# Se a cotação for 0 ou N/A, tratamos para evitar divisão por zero
admanager_current_revenue_usd = admanager_current_revenue_brl / usd_to_brl_rate if usd_to_brl_rate else 0
admanager_previous_revenue_usd = admanager_previous_revenue_brl / usd_to_brl_rate if usd_to_brl_rate else 0

# eCPM = (Ganhos em Dólar / Impressões) * 1000
admanager_current_ecpm = (admanager_current_revenue_usd / admanager_current_impressions * 1000) if admanager_current_impressions else 0
admanager_previous_ecpm = (admanager_previous_revenue_usd / admanager_previous_impressions * 1000) if admanager_previous_impressions else 0


col_usd, col_brl, col_imp, col_ecpm, col_cli = st.columns(5)

with col_usd:
    delta = calculate_percentage_delta(admanager_current_revenue_usd, admanager_previous_revenue_usd)
    # Formatação manual para dólar, usando a lógica de troca de separadores.
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
        value=f"${admanager_current_ecpm:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), # Formatação manual para dólar
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

# Filtrar apenas os dados do Meta Ads para o período atual e anterior
df_meta_ads_current = df_data_current_filtered[df_data_current_filtered['source'] == 'Meta Ads'].copy()
df_meta_ads_previous = df_data_previous_filtered[df_data_previous_filtered['source'] == 'Meta Ads'].copy()

# Calcular métricas do Meta Ads para o período atual
meta_ads_current_cost = df_meta_ads_current['total_custo'].sum()
meta_ads_current_leads = df_meta_ads_current['total_leads'].sum()
meta_ads_current_impressions = df_meta_ads_current['total_impressoes'].sum()
meta_ads_current_clicks = df_meta_ads_current['total_cliques'].sum()

# Calcular métricas do Meta Ads para o período anterior
meta_ads_previous_cost = df_meta_ads_previous['total_custo'].sum()
meta_ads_previous_leads = df_meta_ads_previous['total_leads'].sum()
meta_ads_previous_impressions = df_meta_ads_previous['total_impressoes'].sum()
meta_ads_previous_clicks = df_meta_ads_previous['total_cliques'].sum()

# Calcular métricas derivadas, com tratamento de divisão por zero
meta_ads_current_cpl = meta_ads_current_cost / meta_ads_current_leads if meta_ads_current_leads else 0
meta_ads_current_ctr = (meta_ads_current_clicks / meta_ads_current_impressions * 100) if meta_ads_current_impressions else 0
meta_ads_current_cpm = (meta_ads_current_cost / meta_ads_current_impressions * 1000) if meta_ads_current_impressions else 0
meta_ads_current_cpc = meta_ads_current_cost / meta_ads_current_clicks if meta_ads_current_clicks else 0

meta_ads_previous_cpl = meta_ads_previous_cost / meta_ads_previous_leads if meta_ads_previous_leads else 0
meta_ads_previous_ctr = (meta_ads_previous_clicks / meta_ads_previous_impressions * 100) if meta_ads_previous_impressions else 0
meta_ads_previous_cpm = (meta_ads_previous_cost / meta_ads_previous_impressions * 1000) if meta_ads_previous_impressions else 0
meta_ads_previous_cpc = meta_ads_previous_cost / meta_ads_previous_clicks if meta_ads_previous_clicks else 0


col_gasto, col_leads, col_cpl, col_imp_meta, col_cli_meta = st.columns(5)
col_ctr, col_cpm, col_cpc = st.columns(3) # Segunda linha para as demais métricas

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
        label="Leads",
        value=format_number(meta_ads_current_leads),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_cpl:
    delta = calculate_percentage_delta(meta_ads_current_cpl, meta_ads_previous_cpl)
    st.metric(
        label="CPL",
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
    (df_data_current_filtered['source'] == 'Admanager') & (df_data_current_filtered['dominio'].notna())
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
        
        clean_val = val.replace('R$', '').replace('%', '').replace('.', '').replace(',', '.') if is_currency else val
        try:
            num_val = float(clean_val)
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
st.dataframe(df_data_current_filtered)