import streamlit as st
import datetime
import pandas as pd
import numpy as np
import plotly.express as px

from utils import (
    format_number,
    calculate_business_metrics,
    load_data_for_period,
    TAXA_ADWORK_PERCENT,
    COMISSAO_PERCENT,
    FUNDO_RESERVA_PERCENT,
    get_manager_ranking_data,
    get_project_ranking_data # <<<<< Adicione esta nova importação
)

st.set_page_config(layout="wide", page_title="Dashboard BCF Digital")

# --- Cores customizadas para os cards (baseado no CSS original) ---
CARD_COLORS = {
    "red": "#ef4444",      # Investimento Total
    "blue": "#3b82f6",     # Faturamento
    "green": "#22c55e",    # Receita Líquida
    "purple": "#a855f7",   # ROI Médio
    "purple_light": "#8b5cf6", # Fundo de Reserva
    "orange": "#f97316",   # Comissões
    "green_light": "#16a34a", # Lucro Líquido
    "chart_revenue": "#22c55e", # Cor para receita no gráfico
    "chart_investment": "#ef4444", # Cor para investimento no gráfico
    "chart_profit": "#3b82f6" # Cor para lucro no gráfico
}

# --- Função para criar um card customizado (HTML/CSS inline) ---
def custom_card(title, value, subtitle, background_color, text_color="white", icon=None):
    icon_html = f'<i class="{icon}" style="margin-right: 5px;"></i>' if icon else ''
    st.markdown(
        f"""
        <div style="
            background-color: {background_color};
            color: {text_color};
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        ">
            <p style="font-size: 14px; margin-bottom: 5px; opacity: 0.9;">{icon_html} {title}</p>
            <h3 style="font-size: 28px; font-weight: 700; margin-bottom: 10px; line-height: 1.2;">{value}</h3>
            <p style="font-size: 12px; opacity: 0.7;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Header do Dashboard ---
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 20px; border-bottom: 1px solid #e0e0e0; margin-bottom: 20px; flex-wrap: wrap;">
        <div style="display: flex; flex-direction: column; align-items: flex-start; gap: 5px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-lock" style="font-size: 24px; color: #8b5cf6;"></i>
                <h1 style="font-size: 28px; font-weight: 600; color: #333; margin: 0;">Dashboard BCF Digital</h1>
            </div>
            <p style="font-size: 13px; color: #666; margin-left: 34px;">Visão financeira consolidada · Apenas Admin</p>
            <span style="background-color: #8b5cf6; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 5px; margin-top: 10px; margin-left: 34px;">
                <i class="fas fa-lock" style="font-size: 10px;"></i> Dashboard Privado
            </span>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 5px;">
            <button class="header-button" style="background-color: transparent; border: 1px solid #e0e0e0; color: #666; padding: 8px 15px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-sync-alt"></i> Atualizar
            </button>
            <button class="header-button" style="background-color: transparent; border: 1px solid #e0e0e0; color: #666; padding: 8px 15px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-cog"></i> Configurações
            </button>
            <button class="header-button" style="background-color: transparent; border: 1px solid #e0e0e0; color: #666; padding: 8px 15px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-calculator"></i> Recalcular ROIs
            </button>
            <button class="header-button secondary" style="background-color: #e0e0e0; border-color: #e0e0e0; color: #333; padding: 8px 15px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-tasks"></i> Ações de Lote
            </button>
            <button class="header-button primary" style="background-color: #8b5cf6; border-color: #8b5cf6; color: white; padding: 8px 15px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-plus"></i> Lançar Resultados
            </button>
        </div>
    </div>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    """,
    unsafe_allow_html=True
)

# --- Seletores de Data ---
today = datetime.date.today()
default_start_date = today - datetime.timedelta(days=30)

st.markdown(
    """
    <div style="display: flex; gap: 20px; margin-bottom: 25px; flex-wrap: wrap;">
    """,
    unsafe_allow_html=True
)
col_start_date, col_end_date = st.columns(2)

with col_start_date:
    st.markdown('<label style="font-size: 13px; color: #666; font-weight: 500;">Data Início</label>', unsafe_allow_html=True)
    start_date = st.date_input(
        "data_inicio_financeiro",
        value=default_start_date,
        key="financeiro_start_date",
        label_visibility="collapsed"
    )

with col_end_date:
    st.markdown('<label style="font-size: 13px; color: #666; font-weight: 500;">Data Fim</label>', unsafe_allow_html=True)
    end_date = st.date_input(
        "data_fim_financeiro",
        value=today,
        key="financeiro_end_date",
        label_visibility="collapsed"
    )
st.markdown("</div>", unsafe_allow_html=True)


if start_date > end_date:
    st.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

# --- Carregar e Processar os Dados Base (UMA VEZ) ---
with st.spinner("Carregando e processando dados financeiros..."):
    df_data_raw = load_data_for_period(start_date, end_date)

if df_data_raw.empty:
    st.warning("Nenhum dado encontrado para o período selecionado.")
    st.stop()

# --- Calcular métricas a nível de linha para reutilização ---
# Cria uma cópia para adicionar as colunas processadas sem afetar o df_data_raw
df_data_processed = df_data_raw.copy()
df_data_processed['Lucro_Bruto'] = df_data_processed['total_receita'] - df_data_processed['total_custo']
df_data_processed['Comissao'] = df_data_processed['total_receita'] * COMISSAO_PERCENT
df_data_processed['Lucro_Liquido_Final'] = df_data_processed['Lucro_Bruto'] - df_data_processed['Comissao'] - (df_data_processed['Lucro_Bruto'] * FUNDO_RESERVA_PERCENT)
df_data_processed['ROI_Percentual'] = (
    (df_data_processed['Lucro_Bruto'] / df_data_processed['total_custo']) * 100
).replace([np.inf, -np.inf], np.nan).fillna(0) # Trata divisão por zero


# --- Calcular Métricas para os Cards (usando df_data_processed) ---
# NOTE: calculate_business_metrics em utils.py retorna um dicionário de totais
# e modificava o df. Agora ele DEVE ser ajustado para apenas retornar os totais
# e não modificar df_data_processed.
# Vou assumir que calculate_business_metrics foi ajustado em utils.py
# para apenas retornar as métricas, ou que o cálculo abaixo é o que você precisa.
overall_metrics = {
    'total_receita': df_data_processed['total_receita'].sum(),
    'total_custo': df_data_processed['total_custo'].sum(),
    'lucro_bruto': df_data_processed['Lucro_Bruto'].sum(),
    'comissao': df_data_processed['Comissao'].sum(),
    'fundo_reserva': (df_data_processed['Lucro_Bruto'].sum() * FUNDO_RESERVA_PERCENT),
    'lucro_liquido_final': df_data_processed['Lucro_Liquido_Final'].sum(),
    'roi': (df_data_processed['Lucro_Bruto'].sum() / df_data_processed['total_custo'].sum()) * 100 if df_data_processed['total_custo'].sum() != 0 else 0
}

df_meta_ads = df_data_processed[df_data_processed['source'].str.contains('Meta Ads')]
investimento_total_meta_ads = df_meta_ads['total_custo'].sum()

df_admanager = df_data_processed[df_data_processed['source'].str.contains('Admanager')]
faturamento_admanager_brl = df_admanager['total_receita'].sum()

total_receita_overall = overall_metrics['total_receita']
total_custo_overall = overall_metrics['total_custo']
roi_medio_overall = overall_metrics['roi']

lucro_bruto_overall = overall_metrics['lucro_bruto']
comissoes_overall = overall_metrics['comissao']
fundo_reserva_overall = overall_metrics['fundo_reserva']
lucro_liquido_final_overall = overall_metrics['lucro_liquido_final']


# --- Grid de Cards de Métricas (sempre visível) ---
st.markdown(
    """
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px;">
    """,
    unsafe_allow_html=True
)

col1, col2, col3, col4, col5, col6, col7 = st.columns(7) # 7 colunas para os cards

with col1:
    custom_card(
        "Investimento Total",
        format_number(investimento_total_meta_ads, currency=True),
        "Meta Ads",
        CARD_COLORS["red"]
    )
with col2:
    custom_card(
        "Faturamento",
        format_number(faturamento_admanager_brl, currency=True),
        r"AdSense (US\$) ",
        CARD_COLORS["blue"]
    )
with col3:
    custom_card(
        "Receita Líquida",
        format_number(total_receita_overall * (1 - TAXA_ADWORK_PERCENT), currency=True), # Recalcula aqui se a métrica não estiver em overall_metrics
        "Pós descontos (BRL)",
        CARD_COLORS["green"]
    )
with col4:
    custom_card(
        "ROI Médio",
        format_number(roi_medio_overall, percentage=True, decimal_places=1),
        "Valor no sobre Investimento",
        CARD_COLORS["purple"]
    )
with col5:
    custom_card(
        "Fundo de Reserva",
        format_number(fundo_reserva_overall, currency=True),
        "10% do Lucro Bruto",
        CARD_COLORS["purple_light"]
    )
with col6:
    custom_card(
        "Comissões",
        format_number(comissoes_overall, currency=True),
        "Pagas aos Gestores",
        CARD_COLORS["orange"]
    )
with col7:
    custom_card(
        "Lucro Líquido",
        format_number(lucro_liquido_final_overall, currency=True),
        "Pós Reserva e Comissões",
        CARD_COLORS["green_light"]
    )
st.markdown("</div>", unsafe_allow_html=True)


# --- Seção de Meta Coletiva da Equipe (sempre visível) ---
st.markdown("---")

meta_lucro_valor = 1990000.00  # Valor fixo do print para a meta
status_meta = "Em Progresso"
progress_percentage = (lucro_liquido_final_overall / meta_lucro_valor) * 100 if meta_lucro_valor != 0 else 0

st.markdown(
    f"""
    <div style="background-color: #fff; border: 1px solid #e0e0e0; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <i class="fas fa-users" style="font-size: 20px; color: {CARD_COLORS["purple_light"]};"></i>
            <h3 style="font-size: 18px; font-weight: 600; color: #333; margin: 0;">Meta Coletiva da Equipe</h3>
        </div>
        <p style="font-size: 16px; font-weight: 500; color: #333; margin-bottom: 15px;">Atingir {format_number(meta_lucro_valor, currency=True)} em lucro</p>
        <span style="background-color: #bfdbfe; color: #2563eb; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 20px;">
            {status_meta}
        </span>
        <div style="display: flex; align-items: center;">
            <div style="background-color: #e5e7eb; border-radius: 10px; height: 10px; flex-grow: 1; position: relative;">
                <div style="background-color: {CARD_COLORS["purple_light"]}; height: 100%; border-radius: 10px; width: {min(progress_percentage, 100):.2f}%;"></div>
            </div>
            <span style="font-size: 14px; font-weight: 600; color: #333; margin-left: 15px;">{progress_percentage:.1f}%</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")


# --- Definição das visualizações para os botões de navegação ---
VIEWS = [
    {"id": "overview", "label": "Visão Geral"},
    {"id": "manager", "label": "Por Gestor"},
    {"id": "project", "label": "Por Projeto"}, # <<<<< Este é o botão
    {"id": "daily", "label": "Análise Diária"},
    {"id": "full_table", "label": "Tabela Completa"},
]

# Inicializa o estado da sessão para a visualização ativa
if 'active_view' not in st.session_state:
    st.session_state.active_view = 'overview' # Define 'overview' como padrão

# --- Renderiza os botões de navegação ---
with st.container():
    st.markdown(
        """
        <div style='
            display: flex; 
            gap: 10px; 
            margin-bottom: 20px; 
            flex-wrap: wrap; 
            padding: 10px; 
            border: 1px solid #e0e0e0; 
            border-radius: 8px;
            background-color: #f9f9f9;
            justify-content: center; /* Centraliza os botões no container */
        '>
        """,
        unsafe_allow_html=True
    )
    cols = st.columns(len(VIEWS)) # Cria colunas para cada botão

    for i, view in enumerate(VIEWS):
        is_active = (st.session_state.active_view == view['id'])
        button_type = "primary" if is_active else "secondary"

        with cols[i]:
            if st.button( # Renderiza o botão dentro da coluna
                label=view['label'],
                key=f"tab_button_{view['id']}",
                help=f"Ver {view['label']}",
                type=button_type # Tipo do botão para destaque
            ):
                st.session_state.active_view = view['id']
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("---") # Separador para o conteúdo abaixo dos botões


# --- Conteúdo dinâmico baseado na visualização ativa ---
if st.session_state.active_view == 'overview':
    # --- Preparar dados diários para os gráficos (usando df_data_processed) ---
    df_daily_agg = df_data_processed.groupby('data').agg(
        total_receita=('total_receita', 'sum'),
        total_custo=('total_custo', 'sum'),
        lucro=('Lucro_Bruto', 'sum'), # Usa o lucro bruto pré-calculado
        # O ROI diário é calculado aqui com base no lucro bruto e custo diários agregados.
        # Poderíamos usar 'ROI_Percentual' do df_data_processed, mas a agregação de ROI percentual
        # não é uma soma simples. Recalcular o ROI aqui é o mais correto.
    ).reset_index()

    df_daily_agg['roi'] = (
        (df_daily_agg['lucro'] / df_daily_agg['total_custo']) * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0)


    # --- Layout de Colunas para os Gráficos ---
    chart_col1, chart_col2 = st.columns(2) # Cria duas colunas para os gráficos

    with chart_col1:
        # --- Visualização 1: Desempenho Financeiro (Receita, Investimento, Lucro) ---
        st.markdown("<h3 style='text-align: center; color: #3f51b5; font-size: 1.2em;'>Desempenho Financeiro Diário</h3>", unsafe_allow_html=True)

        # Derreter o DataFrame para facilitar a plotagem de múltiplas barras agrupadas com Plotly Express
        df_melted_financial = df_daily_agg.melt(
            id_vars=['data'],
            value_vars=['total_receita', 'total_custo', 'lucro'],
            var_name='Métrica',
            value_name='Valor'
        )

        # Renomear métricas para exibição amigável
        df_melted_financial['Métrica'] = df_melted_financial['Métrica'].map({
            'total_receita': 'Receita',
            'total_custo': 'Investimento',
            'lucro': 'Lucro'
        })

        # Definir a ordem das barras e cores
        metric_order = ['Receita', 'Investimento', 'Lucro']
        metric_colors = {
            'Receita': CARD_COLORS['chart_revenue'],
            'Investimento': CARD_COLORS['chart_investment'],
            'Lucro': CARD_COLORS['chart_profit']
        }

        fig_financial_perf = px.bar(
            df_melted_financial,
            x='data',
            y='Valor',
            color='Métrica',
            barmode='group', # Barras agrupadas por data
            title='Receita vs. Investimento vs. Lucro', # Título mais conciso para dentro da coluna
            labels={'data': 'Data', 'Valor': 'Valor (R$)', 'Métrica': 'Métrica'},
            color_discrete_map=metric_colors,
            category_orders={'Métrica': metric_order}
        )

        fig_financial_perf.update_layout(hovermode="x unified", title_x=0.5) # Centraliza o título
        fig_financial_perf.update_yaxes(rangemode="tozero", tickprefix="R$ ")
        fig_financial_perf.update_xaxes(tickformat="%d/%m") # Formato de data amigável

        st.plotly_chart(fig_financial_perf, use_container_width=True)

    with chart_col2:
        # --- Visualização 2: Evolução do ROI ---
        st.markdown("<h3 style='text-align: center; color: #3f51b5; font-size: 1.2em;'>Evolução do ROI Diário</h3>", unsafe_allow_html=True)

        fig_roi_evolution = px.line(
            df_daily_agg,
            x='data',
            y='roi',
            title='ROI Diário ao Longo do Tempo', # Título mais conciso para dentro da coluna
            labels={'data': 'Data', 'roi': 'ROI (%)'},
            markers=True,
            color_discrete_sequence=[CARD_COLORS['purple']] # Cor da linha
        )

        fig_roi_evolution.update_layout(hovermode="x unified", title_x=0.5) # Centraliza o título
        fig_roi_evolution.update_yaxes(rangemode="tozero", ticksuffix="%")
        fig_roi_evolution.update_xaxes(tickformat="%d/%m") # Formato de data amigável

        st.plotly_chart(fig_roi_evolution, use_container_width=True)

    st.markdown("---")

elif st.session_state.active_view == 'manager':
    st.markdown("<h2 style='text-align: center; color: #3f51b5;'>Desempenho por Gestor (Ordenado por Lucro)</h2>", unsafe_allow_html=True)

    # Obter os dados de ranking de gestores (passando df_data_processed)
    df_manager_ranking, _ = get_manager_ranking_data(df_data_processed) # Use df_data_processed

    if df_manager_ranking.empty:
        st.warning("Nenhum dado de gestores encontrado para o período selecionado.")
    else:
        # Ordenar pelo Lucro Final (Lucro_Liquido_Final) decrescente
        df_manager_ranking = df_manager_ranking.sort_values(by='Lucro_Liquido_Final', ascending=False).reset_index(drop=True)

        # Preparar o DataFrame para exibição
        df_display = df_manager_ranking[[
            'Gestor', 'Total_Projetos', 'Total_Custo', 'Total_Faturamento',
            'Lucro_Bruto', 'Comissao', 'Lucro_Liquido_Final', 'ROI_Percentual'
        ]].copy()

        # Renomear colunas para exibição
        df_display.columns = [
            'Gestor', 'Projetos', 'Investimento', 'Receita',
            'Lucro Bruto', 'Comissão', 'Lucro Final', 'ROI'
        ]
        
        # --- Cálculo da linha de totalização ---
        total_projetos = df_manager_ranking['Total_Projetos'].sum()
        total_investimento = df_manager_ranking['Total_Custo'].sum()
        total_receita = df_manager_ranking['Total_Faturamento'].sum()
        total_lucro_bruto = df_manager_ranking['Lucro_Bruto'].sum()
        total_comissao = df_manager_ranking['Comissao'].sum()
        total_lucro_final = df_manager_ranking['Lucro_Liquido_Final'].sum()
        total_roi = (total_lucro_bruto / total_investimento) * 100 if total_investimento != 0 else 0

        # DataFrame para a linha de totalização
        df_totals = pd.DataFrame([{
            'Gestor': f"{len(df_manager_ranking)} Gestores",
            'Projetos': total_projetos,
            'Investimento': total_investimento,
            'Receita': total_receita,
            'Lucro Bruto': total_lucro_bruto,
            'Comissão': total_comissao,
            'Lucro Final': total_lucro_final,
            'ROI': total_roi
        }])

        # Concatenar o DataFrame principal com a linha de totalização
        df_final_table = pd.concat([df_display, df_totals], ignore_index=True)

        # Função de estilização para o DataFrame
        def style_manager_table(df):
            styled_df = df.style.format({
                'Projetos': '{:.0f}',
                'Investimento': 'R$ {:,.2f}',
                'Receita': 'R$ {:,.2f}',
                'Lucro Bruto': 'R$ {:,.2f}',
                'Comissão': 'R$ {:,.2f}',
                'Lucro Final': 'R$ {:,.2f}',
                'ROI': '{:,.2f}%'
            }).applymap(lambda x: f'color: {CARD_COLORS["red"]}; font-weight: bold;', 
                        subset=pd.IndexSlice[df.index[:-1], ['Investimento']]) \
              .applymap(lambda x: f'color: {CARD_COLORS["green"]}; font-weight: bold;', 
                        subset=pd.IndexSlice[df.index[:-1], ['Receita', 'Lucro Final', 'ROI']]) \
              .apply(lambda x: ['font-weight: bold; background-color: #f0f2f6;' for _ in x], axis=1, 
                     subset=pd.IndexSlice[df.index[-1], :]) 
            
            styled_df = styled_df.applymap(lambda x: f'color: {CARD_COLORS["red"]}; font-weight: bold;', 
                                            subset=pd.IndexSlice[df.index[-1], ['Investimento']]) \
                                  .applymap(lambda x: f'color: {CARD_COLORS["green"]}; font-weight: bold;', 
                                            subset=pd.IndexSlice[df.index[-1], ['Receita', 'Lucro Final', 'ROI']])
            return styled_df

        st.dataframe(style_manager_table(df_final_table), use_container_width=True, hide_index=True)

elif st.session_state.active_view == 'project': # <<<<< NOVO BLOCO PARA 'POR PROJETO'
    st.markdown("<h2 style='text-align: center; color: #3f51b5;'>Desempenho por Projeto (Ordenado por Lucro)</h2>", unsafe_allow_html=True)

    # Obter os dados de ranking de projetos
    df_project_ranking = get_project_ranking_data(df_data_processed) # Use df_data_processed

    if df_project_ranking.empty:
        st.warning("Nenhum dado de projetos encontrado para o período selecionado.")
    else:
        # Ordenar pelo Lucro_Liquido_Final decrescente
        df_project_ranking = df_project_ranking.sort_values(by='Lucro_Liquido_Final', ascending=False).reset_index(drop=True)

        # Preparar o DataFrame para exibição (renomear colunas para o display final)
        df_display = df_project_ranking.rename(columns={
            'Lucro_Bruto': 'Lucro Bruto',
            'Comissao': 'Comissão',
            'Lucro_Liquido_Final': 'Lucro Final',
            'ROI_Percentual': 'ROI'
        }).copy()
        
        # --- Cálculo da linha de totalização ---
        total_investimento = df_project_ranking['Investimento'].sum()
        total_receita = df_project_ranking['Receita'].sum()
        total_lucro_bruto = df_project_ranking['Lucro_Bruto'].sum()
        total_comissao = df_project_ranking['Comissao'].sum()
        total_lucro_final = df_project_ranking['Lucro_Liquido_Final'].sum()
        total_roi = (total_lucro_bruto / total_investimento) * 100 if total_investimento != 0 else 0

        # DataFrame para a linha de totalização
        df_totals = pd.DataFrame([{
            'Projeto': f"{len(df_project_ranking)} Projetos", # Conta o número de projetos distintos
            'Gestor': 'Todos', # Ou pode deixar vazio ''
            'Investimento': total_investimento,
            'Receita': total_receita,
            'Lucro Bruto': total_lucro_bruto,
            'Comissão': total_comissao,
            'Lucro Final': total_lucro_final,
            'ROI': total_roi
        }])

        # Concatenar o DataFrame principal com a linha de totalização
        df_final_table = pd.concat([df_display, df_totals], ignore_index=True)

        # Função de estilização para o DataFrame (similar à do gestor)
        def style_project_table(df):
            styled_df = df.style.format({
                'Investimento': 'R$ {:,.2f}',
                'Receita': 'R$ {:,.2f}',
                'Lucro Bruto': 'R$ {:,.2f}',
                'Comissão': 'R$ {:,.2f}',
                'Lucro Final': 'R$ {:,.2f}',
                'ROI': '{:,.2f}%'
            }).applymap(lambda x: f'color: {CARD_COLORS["red"]}; font-weight: bold;', 
                        subset=pd.IndexSlice[df.index[:-1], ['Investimento']]) \
              .applymap(lambda x: f'color: {CARD_COLORS["green"]}; font-weight: bold;', 
                        subset=pd.IndexSlice[df.index[:-1], ['Receita', 'Lucro Final', 'ROI']]) \
              .apply(lambda x: ['font-weight: bold; background-color: #f0f2f6;' for _ in x], axis=1, 
                     subset=pd.IndexSlice[df.index[-1], :]) 
            
            styled_df = styled_df.applymap(lambda x: f'color: {CARD_COLORS["red"]}; font-weight: bold;', 
                                            subset=pd.IndexSlice[df.index[-1], ['Investimento']]) \
                                  .applymap(lambda x: f'color: {CARD_COLORS["green"]}; font-weight: bold;', 
                                            subset=pd.IndexSlice[df.index[-1], ['Receita', 'Lucro Final', 'ROI']])
            return styled_df

        st.dataframe(style_project_table(df_final_table), use_container_width=True, hide_index=True)


elif st.session_state.active_view == 'daily':
    st.header("Conteúdo: Análise Diária")
    st.write("Aqui você poderá analisar o desempenho financeiro diário com mais detalhes.")

elif st.session_state.active_view == 'full_table':
    st.header("Conteúdo: Tabela Completa")
    st.write("Aqui você encontrará a tabela completa de todos os dados financeiros brutos.")