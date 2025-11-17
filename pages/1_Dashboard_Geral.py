# pages/1_Dashboard_Geral.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import numpy as np

from utils import (
    format_number, calculate_percentage_delta, calculate_business_metrics,
    load_data_for_period, TAXA_ADWORK_PERCENT, get_usd_to_brl_rate
)

st.set_page_config(layout="wide", page_title="Dashboard de Mídia - Visão Geral")

st.title("Dashboard de Performance de Mídia - Visão Geral")

# --- FILTROS NO CORPO DA PÁGINA ---
col_date_start, col_date_end, col_domain_filter, col_network_code_filter = st.columns([1, 1, 1.5, 1.5])

with col_date_start:
    today = datetime.date.today()
    default_start_date = today - datetime.timedelta(days=30)
    start_date = st.date_input(
        "Data de Início:",
        value=default_start_date,
        max_value=today,
        key='start_date_overview'
    )

with col_date_end:
    end_date = st.date_input(
        "Data de Fim:",
        value=today,
        max_value=today,
        key='end_date_overview'
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

# --- Filtro de Domínio ---
with col_domain_filter:
    st.write("Filtrar por Domínio (Admanager)")
    multiselect_key = 'ms_domains_overview'
    checkbox_key = 'cb_all_domains_overview'
    available_domains_list = list(df_raw_current[
        (df_raw_current['source'] == 'Admanager (UTM)') & (df_raw_current['dominio'].notna())
    ]['dominio'].unique())
    available_domains_list.sort()

    if multiselect_key not in st.session_state:
        st.session_state[multiselect_key] = available_domains_list
    current_selected_valid = [d for d in st.session_state[multiselect_key] if d in available_domains_list]
    if set(current_selected_valid) != set(st.session_state[multiselect_key]):
        st.session_state[multiselect_key] = current_selected_valid

    def on_checkbox_change_overview():
        if st.session_state[checkbox_key]:
            st.session_state[multiselect_key] = available_domains_list
        else:
            st.session_state[multiselect_key] = []
    def on_multiselect_change_overview():
        if set(st.session_state[multiselect_key]) == set(available_domains_list) and len(available_domains_list) > 0:
            st.session_state[checkbox_key] = True
        else:
            st.session_state[checkbox_key] = False

    initial_checkbox_value = (set(st.session_state[multiselect_key]) == set(available_domains_list) and len(available_domains_list) > 0)
    st.checkbox(
        "Selecionar Todos",
        value=initial_checkbox_value,
        key=checkbox_key,
        on_change=on_checkbox_change_overview
    )
    selected_domains = st.multiselect(
        "Selecione os domínios:",
        options=available_domains_list,
        key=multiselect_key,
        label_visibility="collapsed",
        on_change=on_multiselect_change_overview
    )
    if not available_domains_list:
        selected_domains = []

# --- Filtro de Network Code ---
with col_network_code_filter:
    st.write("Filtrar por Network Code (Admanager)")
    multiselect_key_nc = 'ms_network_code_overview'
    checkbox_key_nc = 'cb_all_network_code_overview'
    available_network_codes_list = list(df_raw_current[
        (df_raw_current['source'] == 'Admanager (UTM)') & (df_raw_current['network_code'].notna())
    ]['network_code'].unique())
    available_network_codes_list.sort()

    if multiselect_key_nc not in st.session_state:
        st.session_state[multiselect_key_nc] = available_network_codes_list
    current_selected_valid_nc = [nc for nc in st.session_state[multiselect_key_nc] if nc in available_network_codes_list]
    if set(current_selected_valid_nc) != set(st.session_state[multiselect_key_nc]):
        st.session_state[multiselect_key_nc] = current_selected_valid_nc

    def on_checkbox_change_network_code_overview():
        if st.session_state[checkbox_key_nc]:
            st.session_state[multiselect_key_nc] = available_network_codes_list
        else:
            st.session_state[multiselect_key_nc] = []
    def on_multiselect_change_network_code_overview():
        if set(st.session_state[multiselect_key_nc]) == set(available_network_codes_list) and len(available_network_codes_list) > 0:
            st.session_state[checkbox_key_nc] = True
        else:
            st.session_state[checkbox_key_nc] = False

    initial_checkbox_value_nc = (set(st.session_state[multiselect_key_nc]) == set(available_network_codes_list) and len(available_network_codes_list) > 0)
    st.checkbox(
        "Selecionar Todos",
        value=initial_checkbox_value_nc,
        key=checkbox_key_nc,
        on_change=on_checkbox_change_network_code_overview
    )
    selected_network_codes = st.multiselect(
        "Selecione os Network Codes:",
        options=available_network_codes_list,
        key=multiselect_key_nc,
        label_visibility="collapsed",
        on_change=on_multiselect_change_network_code_overview
    )
    if not available_network_codes_list:
        selected_network_codes = []

# --- Lógica de aplicação dos filtros ---
df_data_current_filtered = df_raw_current.copy()
df_data_previous_filtered = df_raw_previous.copy()

is_admanager_current = (df_data_current_filtered['source'] == 'Admanager (UTM)')
is_admanager_previous = (df_data_previous_filtered['source'] == 'Admanager (UTM)')

if selected_domains:
    domain_filter_current = df_data_current_filtered['dominio'].isin(selected_domains)
    domain_filter_previous = df_data_previous_filtered['dominio'].isin(selected_domains)
    is_admanager_current = is_admanager_current & domain_filter_current
    is_admanager_previous = is_admanager_previous & domain_filter_previous
else:
    st.warning("Nenhum domínio do Admanager selecionado. Os dados de Admanager (UTM) não serão exibidos.")
    is_admanager_current = False
    is_admanager_previous = False

if selected_network_codes:
    network_filter_current = df_data_current_filtered['network_code'].isin(selected_network_codes)
    network_filter_previous = df_data_previous_filtered['network_code'].isin(selected_network_codes)
    is_admanager_current = is_admanager_current & network_filter_current
    is_admanager_previous = is_admanager_previous & network_filter_previous
else:
    if selected_domains:
         st.warning("Nenhum Network Code do Admanager selecionado. Os dados de Admanager (UTM) não serão exibidos.")
    is_admanager_current = False
    is_admanager_previous = False

df_data_current_filtered = df_data_current_filtered[
    (~ (df_data_current_filtered['source'] == 'Admanager (UTM)')) | is_admanager_current
].copy()
df_data_previous_filtered = df_data_previous_filtered[
    (~ (df_data_previous_filtered['source'] == 'Admanager (UTM)')) | is_admanager_previous
].copy()

st.markdown("--- ")

if df_data_current_filtered.empty and df_data_previous_filtered.empty:
    st.warning("Nenhum dado encontrado para o período selecionado e/ou filtros aplicados. Ajuste os filtros ou verifique as fontes de dados.")
    st.stop()

current_metrics = calculate_business_metrics(df_data_current_filtered)
previous_metrics = calculate_business_metrics(df_data_previous_filtered)

usd_to_brl_rate = get_usd_to_brl_rate()

current_total_revenue_usd = current_metrics['total_receita'] / usd_to_brl_rate if usd_to_brl_rate != 0 else 0
previous_total_revenue_usd = previous_metrics['total_receita'] / usd_to_brl_rate if usd_to_brl_rate != 0 else 0

current_adjusted_revenue = current_metrics['total_receita'] - current_metrics['custo_taxa_adwork']
previous_adjusted_revenue = previous_metrics['total_receita'] - previous_metrics['custo_taxa_adwork']


# --- BIG NUMBERS REORGANIZADOS ---
col_custo, col_lucro_liquido, col_receita_usd, col_receita_brl = st.columns(4)
with col_custo:
    delta = calculate_percentage_delta(current_metrics['total_custo'], previous_metrics['total_custo'])
    st.metric(
        label="Custo Total",
        value=format_number(current_metrics['total_custo'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )
with col_lucro_liquido:
    delta = calculate_percentage_delta(current_metrics['lucro_liquido'], previous_metrics['lucro_liquido'])
    st.metric(
        label="Lucro Líquido",
        value=format_number(current_metrics['lucro_liquido'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
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

col_receita_ajustada_2, col_roi, col_roas, col_cliques, col_impressoes = st.columns(5)
with col_receita_ajustada_2:
    delta = calculate_percentage_delta(current_adjusted_revenue, previous_adjusted_revenue)
    st.metric(
        label="Receita Bruta Ajustada",
        value=format_number(current_adjusted_revenue, currency=True),
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
with col_cliques:
    delta = calculate_percentage_delta(current_metrics['total_cliques'], previous_metrics['total_cliques'])
    st.metric(
        label="Cliques",
        value=format_number(current_metrics['total_cliques']),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col_impressoes:
    delta = calculate_percentage_delta(current_metrics['total_impressoes'], previous_metrics['total_impressoes'])
    st.metric(
        label="Impressões",
        value=format_number(current_metrics['total_impressoes']),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )

st.markdown("---")

# Gráfico de Barras Receita vs. Custo ao Longo do Tempo (com grades removidas)
st.subheader("Receita vs. Custo Diário")
df_daily_summary = df_data_current_filtered.groupby('data')[['total_receita', 'total_custo']].sum().reset_index()

fig_rev_cost_daily = go.Figure()

fig_rev_cost_daily.add_trace(go.Bar(
    x=df_daily_summary['data'],
    y=df_daily_summary['total_receita'],
    name='Receita',
    marker_color='green'
))

fig_rev_cost_daily.add_trace(go.Bar(
    x=df_daily_summary['data'],
    y=df_daily_summary['total_custo'],
    name='Custo',
    marker_color='red'
))

fig_rev_cost_daily.update_layout(
    barmode='group',
    title='Receita e Custo Diário',
    xaxis_title=None,
    yaxis_title=None,
    xaxis=dict(showgrid=False, tickformat='%d/%m/%Y'),
    yaxis=dict(showgrid=False),
    legend_title='Métrica'
)
st.plotly_chart(fig_rev_cost_daily, use_container_width=True)


st.markdown("---")
st.subheader("Dados Brutos (Período Atual)")

# --- INÍCIO DAS ALTERAÇÕES PARA A TABELA DE DADOS BRUTOS ---
df_display_raw = df_data_current_filtered.copy()

df_display_raw['dominio'] = df_display_raw['dominio'].fillna('N/A')
df_display_raw['pais'] = df_display_raw['pais'].fillna('N/A')
df_display_raw['network_code'] = df_display_raw['network_code'].fillna('N/A')

rename_map = {
    'total_impressoes': 'impressoes',
    'total_cliques': 'cliques',
    'total_custo': 'custo',
    'total_receita': 'receita',
    'total_leads': 'leads',
    'total_mensagens': 'mensagens'
}
df_display_raw = df_display_raw.rename(columns=rename_map)

group_by_cols = ['data', 'dominio', 'pais', 'network_code']
sum_cols = ['impressoes', 'cliques', 'custo', 'receita', 'leads', 'mensagens']

for col in sum_cols:
    if col not in df_display_raw.columns:
        df_display_raw[col] = 0

df_grouped = df_display_raw.groupby(group_by_cols, as_index=False)[sum_cols].sum()

if df_grouped.empty:
    st.warning("Nenhum dado encontrado para exibir na tabela de dados brutos após o agrupamento. Verifique os filtros ou a integridade dos dados.")
else:
    df_grouped['custo_taxa_adwork_calc'] = df_grouped['receita'] * TAXA_ADWORK_PERCENT
    df_grouped['lucro_liquido'] = df_grouped['receita'] - df_grouped['custo'] - df_grouped['custo_taxa_adwork_calc']

    def calculate_roi_per_row(row):
        if row['custo'] == 0:
            return 0 if row['receita'] == 0 else np.nan # CORRIGIDO: de np.inf para np.nan
        return ((row['receita'] - row['custo']) / row['custo']) * 100

    df_grouped['roi'] = df_grouped.apply(calculate_roi_per_row, axis=1)
    df_grouped = df_grouped.drop(columns=['custo_taxa_adwork_calc'], errors='ignore')

    final_columns_order = [
        'data', 'dominio', 'pais', 'network_code', 'lucro_liquido', 'roi',
        'impressoes', 'cliques', 'custo', 'receita', 'leads', 'mensagens'
    ]
    df_display_raw = df_grouped[final_columns_order]

    # --- NOVO CÓDIGO PARA ADICIONAR LINHA DE SOMATÓRIO (REVISADO) ---
    df_for_overall_metrics = df_display_raw.rename(columns={
        'impressoes': 'total_impressoes',
        'cliques': 'total_cliques',
        'custo': 'total_custo',
        'receita': 'total_receita',
        'leads': 'total_leads',
        'mensagens': 'total_mensagens'
    }).copy()
    
    overall_metrics = calculate_business_metrics(df_for_overall_metrics)

    total_row_data = {
        'data': pd.NaT, # <<<<<<< CORRIGIDO AQUI: de 'Total' para pd.NaT >>>>>>>
        'dominio': '',
        'pais': '',
        'network_code': '',
        'lucro_liquido': overall_metrics['lucro_liquido'],
        'roi': overall_metrics['roi'],
        'impressoes': overall_metrics['total_impressoes'],
        'cliques': overall_metrics['total_cliques'],
        'custo': overall_metrics['total_custo'],
        'receita': overall_metrics['total_receita'],
        'leads': overall_metrics['total_leads'],
        'mensagens': overall_metrics['total_mensagens']
    }

    df_total_row = pd.DataFrame([total_row_data], columns=df_display_raw.columns)
    
    for col in ['lucro_liquido', 'roi', 'impressoes', 'cliques', 'custo', 'receita', 'leads', 'mensagens']:
        if col in df_total_row.columns:
            df_total_row[col] = pd.to_numeric(df_total_row[col], errors='coerce').fillna(0)

    df_display_raw_with_total = pd.concat([df_display_raw, df_total_row], ignore_index=True)

    # --- FIM NOVO CÓDIGO LINHA DE SOMATÓRIO ---

    # 6. Aplicar estilização (heatmap e formatação de números)
    # Definir quais colunas numéricas receberão o heatmap
    numeric_cols_for_heatmap = [
        'lucro_liquido', 'roi', 'impressoes', 'cliques', 'custo', 'receita', 'leads', 'mensagens'
    ]

    # Função auxiliar para criar formatadores para pandas Styler
    def make_styler_formatter_wrapper(currency=False, percentage=False, decimal_places=0):
        return lambda val: format_number(val, currency=currency, percentage=percentage, decimal_places=decimal_places)

    # Dicionário de formatadores para cada coluna
    formatters = {
        'lucro_liquido': make_styler_formatter_wrapper(currency=True, decimal_places=2),
        'roi': make_styler_formatter_wrapper(percentage=True, decimal_places=2),
        'impressoes': make_styler_formatter_wrapper(decimal_places=0),
        'cliques': make_styler_formatter_wrapper(decimal_places=0),
        'custo': make_styler_formatter_wrapper(currency=True, decimal_places=2),
        'receita': make_styler_formatter_wrapper(currency=True, decimal_places=2),
        'leads': make_styler_formatter_wrapper(decimal_places=0),
        'mensagens': make_styler_formatter_wrapper(decimal_places=0),
    }

    # <<<<<<< NOVO FORMATADOR PARA A COLUNA 'DATA' >>>>>>>
    def format_data_column_for_display(val):
        if pd.isna(val): # pd.NaT é considerado NaN
            return "Total"
        return val.strftime('%d/%m/%Y') # Formato original das datas

    formatters['data'] = format_data_column_for_display
    # <<<<<<< FIM NOVO FORMATADOR >>>>>>>

    styled_df = df_display_raw_with_total.style

    total_row_idx = len(df_display_raw_with_total) - 1

    for col_name in numeric_cols_for_heatmap:
        if col_name in df_display_raw_with_total.columns:
            subset_data = pd.to_numeric(df_display_raw_with_total[col_name].iloc[0:total_row_idx], errors='coerce').replace([np.inf, -np.inf], np.nan)
            
            if not subset_data.dropna().empty and subset_data.min() != subset_data.max():
                styled_df = styled_df.background_gradient(
                    cmap='YlGn',
                    subset=pd.IndexSlice[0:total_row_idx-1, col_name] 
                )
    
    # Aplicar os formatadores a todas as colunas, incluindo a linha de total
    # É CRUCIAL que o formatters['data'] seja aplicado aqui para formatar pd.NaT como "Total"
    styled_df = styled_df.format(formatters, na_rep="") 

    # Função para estilizar a linha de total (background cinza e texto em negrito)
    def highlight_total_row_general(row):
        if row.name == total_row_idx:
            return ['background-color: #e0e0e0; font-weight: bold;'] * len(row)
        return [''] * len(row)

    styled_df = styled_df.apply(highlight_total_row_general, axis=1)

    st.dataframe(
        styled_df,
        use_container_width=True
    )