# pages/1_Dashboard_Geral.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import numpy as np # Importar numpy se ainda não estiver

from utils import (
    format_number, calculate_percentage_delta, calculate_business_metrics,
    load_data_for_period, TAXA_ADWORK_PERCENT
)

st.set_page_config(layout="wide", page_title="Dashboard de Mídia - Visão Geral")

st.title("Dashboard de Performance de Mídia - Visão Geral")

# --- FILTROS NO CORPO DA PÁGINA ---
col_date_start, col_date_end, col_domain_filter = st.columns([1, 1, 2]) # Ajusta as larguras das colunas para melhor visualização

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

# --- Filtro de Domínio (Agora na mesma linha das datas) ---
with col_domain_filter: # O filtro de domínio será renderizado nesta terceira coluna
    st.write("Filtrar por Domínio (Admanager)") # Título para a seção de domínio

    # Chaves únicas para os componentes nesta página
    multiselect_key = 'ms_domains_overview'
    checkbox_key = 'cb_all_domains_overview'

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
    def on_checkbox_change_overview():
        if st.session_state[checkbox_key]:
            st.session_state[multiselect_key] = available_domains_list
        else:
            st.session_state[multiselect_key] = []

    # 4. Define a função de callback para o multiselect
    def on_multiselect_change_overview():
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
        on_change=on_checkbox_change_overview # Ativado quando o checkbox é clicado
    )

    # 6. Renderiza o multiselect
    # Seu valor é controlado diretamente por st.session_state[multiselect_key]
    selected_domains = st.multiselect(
        "Selecione os domínios:",
        options=available_domains_list,
        key=multiselect_key, # Chave única para o multiselect
        label_visibility="collapsed",
        on_change=on_multiselect_change_overview # Ativado quando a seleção no multiselect muda
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

current_metrics = calculate_business_metrics(df_data_current_filtered)
previous_metrics = calculate_business_metrics(df_data_previous_filtered)

# ... (Resto do código da página 1_Dashboard_Geral.py permanece o mesmo)
# (Métrics, Gráficos, e Dados Brutos)
# ...

# Métricas de Mídia e Receita
st.subheader("Métricas de Mídia e Receita")
col1, col2, col3, col4 = st.columns(4)

with col1:
    delta = calculate_percentage_delta(current_metrics['total_custo'], previous_metrics['total_custo'])
    st.metric(
        label="Custo Total",
        value=format_number(current_metrics['total_custo'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="inverse"
    )
with col2:
    delta = calculate_percentage_delta(current_metrics['total_receita'], previous_metrics['total_receita'])
    st.metric(
        label="Receita Total",
        value=format_number(current_metrics['total_receita'], currency=True),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col3:
    delta = calculate_percentage_delta(current_metrics['total_cliques'], previous_metrics['total_cliques'])
    st.metric(
        label="Cliques",
        value=format_number(current_metrics['total_cliques']),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )
with col4:
    delta = calculate_percentage_delta(current_metrics['total_impressoes'], previous_metrics['total_impressoes'])
    st.metric(
        label="Impressões",
        value=format_number(current_metrics['total_impressoes']),
        delta=f"{delta:,.2f}%" if delta is not None else None,
        delta_color="normal"
    )

# Métricas de Negócio
st.subheader("Métricas de Negócio")
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


# Gráfico de Barras: Cliques por Fonte (com grades removidas)
st.subheader("Cliques por Fonte")
df_clicks_by_source = df_data_current_filtered.groupby('source')['total_cliques'].sum().reset_index()
fig_clicks = px.bar(
    df_clicks_by_source,
    x="source",
    y="total_cliques",
    title="Total de Cliques por Fonte de Mídia",
    labels={
        "source": "Fonte de Mídia",
        "total_cliques": "Total de Cliques"
    },
    text="total_cliques"
)
fig_clicks.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
fig_clicks.update_layout(
    xaxis_title=None,
    yaxis_title=None,
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False)
)
st.plotly_chart(fig_clicks, use_container_width=True)

# Gráfico de Pizza/Donut: Custo por Fonte (gráfico de pizza não tem grades tradicionais de eixo)


st.markdown("---")
st.subheader("Dados Brutos (Período Atual)")
st.dataframe(df_data_current_filtered)