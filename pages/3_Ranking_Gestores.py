# pages/3_Ranking_Gestores.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# Import the functions and constants from your utils.py
from utils import load_data_for_period, get_previous_month_overall_faturamento, get_manager_ranking_data, format_number, COMISSAO_PERCENT

st.set_page_config(layout="wide", page_title="📊 Ranking de Gestores")

st.title("📊 Ranking de Gestores")

# --- Filtros de Desempenho (na área principal) ---
st.markdown("### Filtros de Desempenho")
col_date_start, col_date_end, col_manager_filter = st.columns([1, 1, 2]) # Layout para os filtros

today = datetime.now().date()
default_start_date = today - timedelta(days=30)
default_end_date = today

with col_date_start:
    start_date = st.date_input("Data de Início", default_start_date)
with col_date_end:
    end_date = st.date_input("Data de Fim", default_end_date)

# Validação de data
if start_date > end_date:
    st.error("Erro: A data de início não pode ser maior que a data de fim.")
    st.stop() # Interrompe a execução se as datas forem inválidas

# --- Carregar Dados Brutos de Performance (uma vez para todo o app) ---
with st.spinner("Carregando dados de performance do BigQuery..."):
    df_ad_performance_raw = load_data_for_period(start_date, end_date) # Carrega os dados brutos

# --- Agrega dados por gestores (usando os dados brutos de performance) ---
with st.spinner("Processando dados de gestores..."):
    df_ranking_raw, df_daily_performance_with_managers_raw = get_manager_ranking_data(df_ad_performance_raw) # Obtém ambos os DataFrames

if not df_ranking_raw.empty:
    # Obter gestores únicos para o filtro, APÓS o carregamento dos dados
    all_managers = sorted(df_ranking_raw['Gestor'].unique().tolist())
    
    with col_manager_filter: # Esta é a terceira coluna para filtros
        selected_managers = st.multiselect(
            "Filtrar por Gestor(es)",
            options=all_managers,
            default=all_managers # Por padrão, todos os gestores são selecionados
        )

    # Aplicar filtro de gestores
    if selected_managers:
        df_ranking_filtered = df_ranking_raw[df_ranking_raw['Gestor'].isin(selected_managers)]
        # Filtrar o DataFrame diário também pelos gestores selecionados
        df_daily_performance_filtered = df_daily_performance_with_managers_raw[
            df_daily_performance_with_managers_raw['Gestor'].isin(selected_managers)
        ]
    else:
        df_ranking_filtered = df_ranking_raw.copy() # Se nenhum gestor for selecionado, mostra todos
        df_daily_performance_filtered = df_daily_performance_with_managers_raw.copy()
        st.warning("Nenhum gestor selecionado. Exibindo dados de todos os gestores.")
    
    # Se, após o filtro, o DataFrame de ranking estiver vazio, exibir mensagem e parar
    if df_ranking_filtered.empty:
        st.info("Nenhum dado encontrado para os gestores e período selecionados.")
        st.stop()

    st.markdown("---") # Separador visual

    # --- Calcular e Exibir Métricas de Resumo Geral (Cards) ---
    st.markdown("<h3 style='text-align: center; color: #3f51b5;'>Resumo do Período (Gestores Selecionados)</h3>", unsafe_allow_html=True)
    st.write("---")

    # Calcula os totais gerais somando todas as métricas dos gestores FILTRADOS
    overall_investimento = df_ranking_filtered['Total_Custo'].sum()
    overall_faturamento = df_ranking_filtered['Total_Faturamento'].sum()
    overall_lucro_bruto_dbl = df_ranking_filtered['Lucro_Bruto'].sum()
    overall_comissao = df_ranking_filtered['Comissao'].sum()
    overall_fundo_reserva = df_ranking_filtered['Fundo_Reserva'].sum()
    overall_lucro_liquido_final = df_ranking_filtered['Lucro_Liquido_Final'].sum()
    
    # Calcular ROI geral com base nos totais
    overall_roi_percentual = (overall_lucro_bruto_dbl / overall_investimento * 100) if overall_investimento != 0 else np.nan
    overall_roas = (overall_faturamento / overall_investimento) if overall_investimento != 0 else np.nan


    # Primeira linha de cards (4 colunas)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"##### 💰 Investimento")
        st.markdown(f"<h2 style='color: #f87171;'>{format_number(overall_investimento, currency=True)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>Total (Meta Ads)</p>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"##### �� Faturamento")
        st.markdown(f"<h2 style='color: #60a5fa;'>{format_number(overall_faturamento, currency=True)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>Total (AdX + Meta)</p>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"##### 💸 Receita Líquida")
        st.markdown(f"<h2 style='color: #4ade80;'>{format_number(overall_lucro_bruto_dbl, currency=True)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>Líquida (DBL)</p>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"##### �� ROI Médio")
        st.markdown(f"<h2 style='color: #a78bfa;'>{format_number(overall_roi_percentual, percentage=True, decimal_places=2)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>Média do Período</p>", unsafe_allow_html=True)

    # Segunda linha de cards (3 colunas)
    col5, col6, col7 = st.columns(3) 

    with col5:
        st.markdown(f"##### 🏦 Fundo Reserva")
        st.markdown(f"<h2 style='color: #c4b5fd;'>{format_number(overall_fundo_reserva, currency=True)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>10% do Lucro Bruto</p>", unsafe_allow_html=True)
    with col6:
        st.markdown(f"##### 💵 Lucro Final")
        st.markdown(f"<h2 style='color: #86efac;'>{format_number(overall_lucro_liquido_final, currency=True)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>Pós Reserva e Comissão</p>", unsafe_allow_html=True)
    with col7:
        st.markdown(f"##### ⚡ Comissão")
        st.markdown(f"<h2 style='color: #fbbf24;'>{format_number(overall_comissao, currency=True)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; font-size: 0.8em;'>3% - Comissão padrão</p>", unsafe_allow_html=True)
    
    st.write("---") 

    # --- Calcular Meta de Faturamento Mensal ---
    st.markdown("<h3 style='text-align: center; color: #3f51b5;'>🎯 Meta de Faturamento Mensal</h3>", unsafe_allow_html=True)

    # Usar o faturamento total bruto (sem filtro de gestor, para a meta geral)
    # df_ad_performance_raw já é o dataframe não filtrado por gestor, mas filtrado por data
    overall_faturamento_for_current_period_no_manager_filter = df_ad_performance_raw['total_receita'].sum()

    with st.spinner("Calculando faturamento do mês anterior para meta..."):
        previous_month_faturamento = get_previous_month_overall_faturamento(start_date)

    GOAL_INCREASE_PERCENT = 0.10 # 10% de aumento sobre o faturamento do faturamento do mês anterior
    current_month_goal = previous_month_faturamento * (1 + GOAL_INCREASE_PERCENT) if previous_month_faturamento > 0 else 0.0

    current_month_name = end_date.strftime('%B') # Nome do mês da data final do filtro

    # Cards da meta
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.markdown(f"**Faturamento Mês Anterior**")
        st.markdown(f"<h3 style='color: #60a5fa;'>{format_number(previous_month_faturamento, currency=True)}</h3>", unsafe_allow_html=True)
    with col_meta2:
        st.markdown(f"**Meta do Mês ({current_month_name})**")
        st.markdown(f"<h3 style='color: #4ade80;'>{format_number(current_month_goal, currency=True)}</h3>", unsafe_allow_html=True)

    # Progresso da meta
    st.write("---")
    if current_month_goal > 0:
        progress_percent = (overall_faturamento_for_current_period_no_manager_filter / current_month_goal * 100)
        faltam_para_o_mes = current_month_goal - overall_faturamento_for_current_period_no_manager_filter
        st.markdown(f"**Progresso do Mês ({current_month_name}):**")
        st.progress(min(float(progress_percent / 100), 1.0), text=f"{progress_percent:.2f}%")

        col_progress1, col_progress2 = st.columns(2)
        with col_progress1:
            st.markdown(f"**Atual do Mês**")
            st.markdown(f"<h3 style='color: #60a5fa;'>{format_number(overall_faturamento_for_current_period_no_manager_filter, currency=True)}</h3>", unsafe_allow_html=True)
        with col_progress2:
            st.markdown(f"**Faltam para o Mês**")
            st.markdown(f"<h3 style='color: #f87171;'>{format_number(faltam_para_o_mes, currency=True)}</h3>", unsafe_allow_html=True)
    else:
        st.info("Não foi possível calcular a meta mensal, pois o faturamento do mês anterior é zero ou não disponível.")
    st.write("---")

    # --- Métricas Adicionais do Período (Tabela de Resumo) ---
    st.markdown("<h3 style='text-align: center; color: #3f51b5;'>Métricas Adicionais do Período</h3>", unsafe_allow_html=True)
    st.write("---")

    # Criar DataFrame para a tabela de resumo
    summary_data = {
        "Métrica": [
            "Investimento Total",
            "Receita R\$ Total", # Renomeado para Receita R\$
            "Lucro Bruto Total",
            "Comissão Total",
            "Fundo Reserva Total",
            "Lucro Líquido Final Total",
            "ROI Médio",
            "ROAS Médio",
        ],
        "Valor": [
            format_number(overall_investimento, currency=True),
            format_number(overall_faturamento, currency=True), # Faturamento se torna Receita R\$
            format_number(overall_lucro_bruto_dbl, currency=True),
            format_number(overall_comissao, currency=True),
            format_number(overall_fundo_reserva, currency=True),
            format_number(overall_lucro_liquido_final, currency=True),
            format_number(overall_roi_percentual, percentage=True, decimal_places=2),
            format_number(overall_roas, x_suffix=True, decimal_places=1), # ROAS com sufixo 'x' e 1 casa decimal
        ]
    }
    df_summary_table = pd.DataFrame(summary_data)
    st.dataframe(df_summary_table, hide_index=True, width='stretch')

    st.write("---") 
    
    # --- Evolução do ROI (Média por Dia) ---
    st.markdown("<h3 style='text-align: center; color: #3f51b5;'>Evolução do ROI (Média por Dia)</h3>", unsafe_allow_html=True)
    st.write("---")

    if not df_daily_performance_filtered.empty:
        # Agrupar por dia para calcular o ROI diário consolidado para os gestores selecionados
        df_daily_roi = df_daily_performance_filtered.groupby('data').agg(
            total_receita=('total_receita', 'sum'),
            total_custo=('total_custo', 'sum')
        ).reset_index()

        df_daily_roi['Lucro_Bruto'] = df_daily_roi['total_receita'] - df_daily_roi['total_custo']
        
        # Evitar divisão por zero no ROI
        df_daily_roi['ROI_Percentual'] = (
            (df_daily_roi['Lucro_Bruto'] / df_daily_roi['total_custo']) * 100
        ).replace([np.inf, -np.inf], np.nan).fillna(0) # Substitui infinitos por 0 ou NaN se preferir

        fig_roi = px.line(
            df_daily_roi,
            x='data',
            y='ROI_Percentual',
            title='Evolução do ROI (Média por Dia)',
            labels={'data': 'Data', 'ROI_Percentual': 'ROI (%)'},
            markers=True 
        )
        fig_roi.update_layout(hovermode="x unified") 
        fig_roi.update_yaxes(rangemode="tozero", ticksuffix="%") 
        st.plotly_chart(fig_roi, use_container_width=True)
    else:
        st.info("Nenhum dado diário de performance encontrado para calcular o ROI para os gestores selecionados.")

    st.write("---") 

    # --- Tabela de Desempenho Diário Consolidado (Tabela do Print) ---
    st.markdown("<h3 style='text-align: center; color: #3f51b5;'>ROI Dia a Dia - Tabela Detalhada</h3>", unsafe_allow_html=True)
    st.write("---")

    if not df_daily_performance_filtered.empty:
        # --- CORREÇÃO AQUI: Duas etapas para agregação e renomeação ---
        # Etapa 1: Agrupar por 'data' e somar as colunas originais
        df_daily_consolidated_full_temp = df_daily_performance_filtered.groupby('data').agg({
            'total_custo': 'sum',
            'total_receita': 'sum',
            'Lucro_Bruto': 'sum'
        }).reset_index()

        # Etapa 2: Renomear as colunas para os nomes desejados
        df_daily_consolidated_full = df_daily_consolidated_full_temp.rename(columns={
            'total_custo': 'Investimento',
            'total_receita': 'Receita_R$',
            'Lucro_Bruto': 'Lucro'
        })
        # --- Fim da correção ---

        # Calcular as métricas adicionais por dia
        df_daily_consolidated_full['Comissao'] = df_daily_consolidated_full['Receita_R$'] * COMISSAO_PERCENT
        df_daily_consolidated_full['ROI'] = (df_daily_consolidated_full['Lucro'] / df_daily_consolidated_full['Investimento'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
        df_daily_consolidated_full['ROAS'] = (df_daily_consolidated_full['Receita_R$'] / df_daily_consolidated_full['Investimento']).replace([np.inf, -np.inf], np.nan).fillna(0)
        df_daily_consolidated_full['Status'] = df_daily_consolidated_full['Lucro'].apply(lambda x: 'Positivo' if x >= 0 else 'Negativo')

        # Selecionar e renomear colunas para a exibição na tabela, na ordem exata do print
        df_table_display_print = df_daily_consolidated_full[[
            'data', 'Investimento', 'Receita_R$', 'Lucro', 'Comissao', 'ROI', 'ROAS', 'Status'
        ]].copy()
        
        # Renomear 'Receita_R$' para 'Receita R\$' (apenas para exibição)
        df_table_display_print.rename(columns={'Receita_R$': 'Receita R\$'}, inplace=True)

        # Formatar colunas para exibição
        df_table_display_print['data'] = df_table_display_print['data'].dt.strftime('%d/%m/%Y')
        for col in ['Investimento', 'Receita R\$', 'Lucro', 'Comissao']:
            df_table_display_print[col] = df_table_display_print[col].apply(lambda x: format_number(x, currency=True))
        df_table_display_print['ROI'] = df_table_display_print['ROI'].apply(lambda x: format_number(x, percentage=True, decimal_places=1)) # 1 casa decimal para ROI
        df_table_display_print['ROAS'] = df_table_display_print['ROAS'].apply(lambda x: format_number(x, x_suffix=True, decimal_places=1)) # ROAS com sufixo 'x'

        st.dataframe(df_table_display_print, hide_index=True, width='stretch')
        st.markdown(
            "***Nota:** A coluna 'Receita $' do print original não é incluída diretamente aqui, pois toda a receita é convertida para R\$ no carregamento de dados. A coluna 'Receita R\$' representa o faturamento total em reais.*"
        )
    else:
        st.info("Nenhum dado diário de performance encontrado para exibir a tabela detalhada.")

    st.write("---")

    # --- Manager Ranking Selection and Display ---
    st.subheader("Ranking Individual de Gestores")
    metricas_ranking = {
        "Total Faturamento": "Total_Faturamento",
        "Total Custo": "Total_Custo",
        "Lucro Bruto": "Lucro_Bruto",
        "Lucro Líquido Final": "Lucro_Liquido_Final",
        "Comissão": "Comissao",
        "Fundo Reserva": "Fundo_Reserva",
        "ROI (%)": "ROI_Percentual", 
        "ROAS": "ROAS",
        "Total Impressões": "Total_Impressoes",
        "Total Cliques": "Total_Cliques"
    }
    selected_metric_display = st.selectbox(
        "Escolha a métrica para rankear os gestores:",
        list(metricas_ranking.keys()),
        index=3 
    )
    selected_metric_column = metricas_ranking[selected_metric_display]

    df_ranking_sorted = df_ranking_filtered.sort_values(by=selected_metric_column, ascending=False).reset_index(drop=True)

    st.write("### Tabela de Ranking Detalhada")
    display_df = df_ranking_sorted.copy()
    
    for col in ['Total_Faturamento', 'Total_Custo', 'Lucro_Bruto', 'Comissao', 'Fundo_Reserva', 'Lucro_Liquido_Final']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: format_number(x, currency=True))
    
    if 'ROI_Percentual' in display_df.columns:
        display_df['ROI_Percentual'] = display_df['ROI_Percentual'].apply(lambda x: format_number(x, percentage=True, decimal_places=2))
    if 'ROAS' in display_df.columns:
        display_df['ROAS'] = display_df['ROAS'].apply(lambda x: format_number(x, x_suffix=True, decimal_places=1)) # ROAS com sufixo 'x'
    if 'Total_Impressoes' in display_df.columns:
        display_df['Total_Impressoes'] = display_df['Total_Impressoes'].apply(lambda x: format_number(x, decimal_places=0))
    if 'Total_Cliques' in display_df.columns:
        display_df['Total_Cliques'] = display_df['Total_Cliques'].apply(lambda x: format_number(x, decimal_places=0))

    st.dataframe(display_df, width='stretch')

    st.write(f"### Gráfico de Ranking por {selected_metric_display}")

    y_axis_prefix = ""
    y_axis_suffix = ""
    if selected_metric_column in ['Total_Faturamento', 'Total_Custo', 'Lucro_Bruto', 'Comissao', 'Fundo_Reserva', 'Lucro_Liquido_Final']:
        y_axis_prefix = "R\$ "
    elif selected_metric_column == 'ROI_Percentual':
        y_axis_suffix = "%"
    
    fig = px.bar(
        df_ranking_sorted,
        x="Gestor",
        y=selected_metric_column,
        title=f"Ranking de Gestores por {selected_metric_display}",
        labels={
            "Gestor": "Gestor",
            selected_metric_column: selected_metric_display
        },
        color=selected_metric_column, 
        color_continuous_scale=px.colors.sequential.Greens 
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'}) 
    fig.update_yaxes(tickprefix=y_axis_prefix, ticksuffix=y_axis_suffix)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Nenhum dado de ranking de gestores encontrado para o período selecionado.")