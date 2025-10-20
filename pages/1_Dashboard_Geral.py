# pages/1_Dashboard_Geral.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from utils import (
    format_number, calculate_percentage_delta, calculate_business_metrics,
    load_data_for_period, TAXA_ADWORK_PERCENT
)

st.set_page_config(layout="wide", page_title="Dashboard de Mídia - Visão Geral")

st.title("📊 Dashboard de Performance de Mídia - Visão Geral")

# --- FILTROS NO CORPO DA PÁGINA ---
st.subheader("Filtros")

col_date1, col_date2 = st.columns(2)

with col_date1:
    today = datetime.date.today()
    default_start_date = today - datetime.timedelta(days=30)
    start_date = st.date_input(
        "Data de Início:",
        value=default_start_date,
        max_value=today,
        key='start_date_overview'
    )

with col_date2:
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

# --- Filtro de Domínio (Revertido para a versão anterior) ---
available_domains = df_raw_current[
    (df_raw_current['source'] == 'Admanager') & (df_raw_current['dominio'].notna())
]['dominio'].unique()
available_domains.sort()

st.write("### Filtrar por Domínio (Admanager)") # Subtítulo para os filtros de domínio
col_domain_checkbox, col_domain_select = st.columns([0.3, 0.7]) # Ajusta as larguras das colunas

with col_domain_checkbox:
    select_all_domains = st.checkbox("Selecionar Todos", value=True, key='checkbox_all_domains_overview')

with col_domain_select:
    if select_all_domains:
        default_selected_domains = list(available_domains)
    else:
        default_selected_domains = []

    selected_domains = st.multiselect(
        "Selecione os domínios:",
        options=list(available_domains),
        default=default_selected_domains,
        key='multiselect_domains_overview',
        label_visibility="collapsed" # Oculta o label do multiselect pois já tem o checkbox
    )

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

# --- Exibição dos Dados e Métricas ---
st.subheader(f"Performance de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")

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
st.subheader("Distribuição de Custo por Fonte")
df_cost_by_source = df_data_current_filtered.groupby('source')['total_custo'].sum().reset_index()
fig_cost_pie = px.pie(
    df_cost_by_source,
    values="total_custo",
    names="source",
    title="Custo Total por Fonte de Mídia",
    hole=0.3,
    labels={
        "total_custo": "Custo",
        "source": "Fonte de Mídia"
    }
)
st.plotly_chart(fig_cost_pie, use_container_width=True)

st.markdown("---")
st.subheader("Dados Brutos (Período Atual)")
st.dataframe(df_data_current_filtered)