import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# 1. CONFIGURAÇÕES INICIAIS DA PÁGINA
st.set_page_config(page_title="Sistema Lenoor - Orçamentos v3", page_icon="⚙️", layout="wide")

# Nome do arquivo de banco de dados local
ARQUIVO_HISTORICO = "historico_orcamentos_estruturado.csv"

# Constantes fixas de materiais
DADOS_MATERIAIS = {
    "aço sx": 0.68, "aço red": 0.62, "aço quad": 0.72,
    "aluminio red": 0.212, "aluminio quad": 0.212, "aluminio sx": 0.212,
    "latao red": 0.68, "latao quad": 0.78, "latao sx": 0.72
}

# 2. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO
if "valores_maquinas" not in st.session_state:
    st.session_state.valores_maquinas = {
        "CNC": 150.0, "Torno Automático": 120.0, "Freza": 120.0,
        "Furadeira": 70.0, "Torno Revolver": 90.0, "Retífica": 150.0,
        "Serra": 70.0, "Montagem": 90.0, "Outro": 150.0
    }
if "impostos" not in st.session_state:
    st.session_state.impostos = {"IR": 6.0, "FS": 4.0}
if "dados_carregados" not in st.session_state:
    st.session_state.dados_carregados = {}
if "mensagem_sucesso" not in st.session_state:
    st.session_state.mensagem_sucesso = ""

# Inicialização padrão de chaves para evitar loops visuais do Streamlit
if "sel_empresa_aba1" not in st.session_state: st.session_state["sel_empresa_aba1"] = ""
if "txt_comprador" not in st.session_state: st.session_state["txt_comprador"] = ""
if "sel_codigo_peca" not in st.session_state: st.session_state["sel_codigo_peca"] = ""
if "txt_novo_codigo" not in st.session_state: st.session_state["txt_novo_codigo"] = ""
if "txt_nome_peca" not in st.session_state: st.session_state["txt_nome_peca"] = ""
if "num_lote" not in st.session_state: st.session_state["num_lote"] = 100
if "num_comprimento" not in st.session_state: st.session_state["num_comprimento"] = 0.0
if "num_margem_corte" not in st.session_state: st.session_state["num_margem_corte"] = 5.0
if "sel_tipo_mp" not in st.session_state: st.session_state["sel_tipo_mp"] = "Por Peso (Barra Maciça/Sextavada)"
if "num_preco_mp" not in st.session_state: st.session_state["num_preco_mp"] = 0.0
if "sel_liga" not in st.session_state: st.session_state["sel_liga"] = "aço sx"
if "num_diam_barra" not in st.session_state: st.session_state["num_diam_barra"] = 15.0
if "num_di_ext" not in st.session_state: st.session_state["num_di_ext"] = 20.0
if "num_di_int" not in st.session_state: st.session_state["num_di_int"] = 10.0
if "num_peso_metro" not in st.session_state: st.session_state["num_peso_metro"] = 10.0
if "num_peso_peca" not in st.session_state: st.session_state["num_peso_peca"] = 10.0
if "num_peso_fornecido" not in st.session_state: st.session_state["num_peso_fornecido"] = 0.0
if "slider_lucro_aba1" not in st.session_state: st.session_state["slider_lucro_aba1"] = 30

if "df_usinagem_v3" not in st.session_state:
    st.session_state["df_usinagem_v3"] = pd.DataFrame([{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50}])
if "df_tratamento_v3" not in st.session_state:
    st.session_state["df_tratamento_v3"] = pd.DataFrame([{"Tratamento": "Nenhum / Sem Tratamento", "Preço por Kg (R$)": 0.0}])

# Carrega listas do histórico para sugestão automática
lista_empresas = []
lista_codigos = []
if os.path.exists(ARQUIVO_HISTORICO):
    try:
        df_init = pd.read_csv(ARQUIVO_HISTORICO)
        lista_empresas = sorted(df_init["Empresa"].dropna().unique().tolist())
        lista_codigos = sorted(df_init["Código da Peça"].dropna().unique().tolist())
    except:
        pass

# --- FUNÇÃO DE CALLBACK PARA AUTOCOMPLETE SEGURO ---
def carregar_roteiro_antigo_callback():
    codigo_target = st.session_state["sel_codigo_peca"]
    if codigo_target and codigo_target != "➕ Novo Código..." and os.path.exists(ARQUIVO_HISTORICO):
        try:
            df_hist_busca = pd.read_csv(ARQUIVO_HISTORICO)
            df_filtrado = df_hist_busca[df_hist_busca["Código da Peça"] == codigo_target]
            if not df_filtrado.empty:
                last_hist = df_filtrado.iloc[-1].to_dict()
                st.session_state["dados_carregados"] = last_hist
                
                # Injeta os dados históricos na memória do app de forma segura
                st.session_state["sel_empresa_aba1"] = last_hist.get("Empresa", "")
                st.session_state["txt_comprador"] = last_hist.get("Comprador", "")
                st.session_state["txt_nome_peca"] = last_hist.get("Nome da Peça", "")
                st.session_state["num_lote"] = int(last_hist.get("Lote", 100))
                st.session_state["num_comprimento"] = float(last_hist.get("Comprimento (mm)", 0.0))
                st.session_state["num_margem_corte"] = float(last_hist.get("Margem Corte (mm)", 5.0))
                st.session_state["sel_tipo_mp"] = last_hist.get("Tipo MP", "Por Peso (Barra Maciça/Sextavada)")
                st.session_state["num_preco_mp"] = float(last_hist.get("Preço MP Unitário", 0.0))
                st.session_state["sel_liga"] = last_hist.get("Liga", "aço sx")
                st.session_state["num_diam_barra"] = float(last_hist.get("Diâmetro (mm)", 15.0))
                st.session_state["num_di_ext"] = float(last_hist.get("Diâmetro Externo (mm)", 20.0))
                st.session_state["num_di_int"] = float(last_hist.get("Diâmetro Interno (mm)", 10.0))
                st.session_state["num_peso_metro"] = float(last_hist.get("Total Kg Lote", 10.0))
                st.session_state["num_peso_peca"] = float(last_hist.get("Total Kg Lote", 10.0))
                st.session_state["num_peso_fornecido"] = float(last_hist.get("Total Kg Lote", 0.0))
                st.session_state["slider_lucro_aba1"] = int(last_hist.get("Margem Lucro (%)", 30))
                
                if "Usinagem_JSON" in last_hist:
                    st.session_state["df_usinagem_v3"] = pd.read_json(last_hist["Usinagem_JSON"])
                if "Tratamento_JSON" in last_hist:
                    st.session_state["df_tratamento_v3"] = pd.read_json(last_hist["Tratamento_JSON"])
                    
                if "editor_usinagem_aba1" in st.session_state: del st.session_state["editor_usinagem_aba1"]
                if "editor_tratamentos_aba1" in st.session_state: del st.session_state["editor_tratamentos_aba1"]
                
                st.session_state["mensagem_sucesso"] = "📋 Dados e roteiros antigos restaurados com sucesso para a tela!"
        except:
            pass

valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos

# =============================================================================
# 🧭 NAVEGAÇÃO LATERAL (BLINDAGEM CONTRA MIX DE ABAS)
# =============================================================================
st.sidebar.title("🧭 Menu Lenoor")
opcao_menu = st.sidebar.radio(
    "Selecione a tela ativa:",
    [
        "📊 1. Novo Orçamento", 
        "📜 2. Histórico & Preços Atuais", 
        "⚙️ 3. Configurações de Custos e Impostos"
    ]
)
st.sidebar.markdown("---")
st.sidebar.caption("Lenoor S/A v3.1 - Estabilidade Total")

# Título Estático Principal
st.title("Sistema Lenoor de Orçamentos")

# Exibe a mensagem de sucesso se ela existir na sessão
if st.session_state.mensagem_sucesso:
    st.success(st.session_state.mensagem_sucesso)
    st.session_state.mensagem_sucesso = "" 

st.markdown(f"**Navegação atual:** {opcao_menu}")
st.markdown("---")

# =============================================================================
# TELA 1: NOVO ORÇAMENTO
# =============================================================================
if opcao_menu == "📊 1. Novo Orçamento":
    # --- BLOCO 1: DADOS DO CLIENTE ---
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    
    hist = st.session_state.dados_carregados
    
    with col_cli1:
        opcoes_empresa = [""] + lista_empresas + ["➕ Novo Cliente..."]
        if st.session_state["sel_empresa_aba1"] not in opcoes_empresa and st.session_state["sel_empresa_aba1"] != "":
            opcoes_empresa.insert(1, st.session_state["sel_empresa_aba1"])
            
        empresa_sel = st.selectbox("Empresa/Cliente", opcoes_empresa, key="sel_empresa_aba1")
        if empresa_sel == "➕ Novo Cliente...":
            empresa = st.text_input("Digite o nome do Novo Cliente", placeholder="Ex: TS", key="txt_nova_empresa")
        else:
            empresa = empresa_sel
            
    with col_cli2:
        comprador = st.text_input("Comprador Responsável", placeholder="Ex: Guilherme", key="txt_comprador")

    st.markdown("---")
    
    # --- BLOCO 2: DADOS DO PRODUTO (ALINHADOS LADO A LADO) ---
    st.subheader("📦 Dados do Produto")
    col_cod_linha1, col_cod_linha2 = st.columns([3, 1])
    
    with col_cod_linha1:
        opcoes_codigo = [""] + lista_codigos + ["➕ Novo Código..."]
        if st.session_state["sel_codigo_peca"] not in opcoes_codigo and st.session_state["sel_codigo_peca"] != "":
            opcoes_codigo.insert(1, st.session_state["sel_codigo_peca"])
            
        codigo_sel = st.selectbox("Código da Peça (Selecione ou digite para buscar)", opcoes_codigo, key="sel_codigo_peca")
        
        # Input blindado para novos códigos (o teclado não perde mais o foco!)
        if codigo_sel == "➕ Novo Código...":
            codigo_peca = st.text_input("Escreva o Código Novo do Produto:", placeholder="Ex: TS-8-030-XXXX", key="txt_novo_codigo")
        else:
            codigo_peca = codigo_sel

    with col_cod_linha2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True) 
        if codigo_sel and codigo_sel != "➕ Novo Código..." and os.path.exists(ARQUIVO_HISTORICO):
            st.button("📋 Completar dados", type="secondary", use_container_width=True, on_click=carregar_roteiro_antigo_callback)

    col_dados_p1, col_dados_p2, col_dados_p3, col_dados_p4 = st.columns(4)
    with col_dados_p1:
        nome_peca = st.text_input("Nome da Peça", key="txt_nome_peca")
    with col_dados_p2:
        lote = st.number_input("Quantidade do Lote", min_value=1, step=1, key="num_lote")
    with col_dados_p3:
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, step=0.1, key="num_comprimento")
    with col_dados_p4:
        margem_corte = st.number_input("Margem de Corte/Perda (mm)", min_value=0.0, step=0.1, key="num_margem_corte")

    st.markdown("---")

    # --- BLOCO 3: MATÉRIA-PRIMA CONDICIONAL REAL ---
    st.subheader("🧱 Definição da Matéria-Prima")
    opcoes_mp = ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Fornecido pelo Cliente (Mão de Obra Pura)"]
    if st.session_state["sel_tipo_mp"] not in opcoes_mp: st.session_state["sel_tipo_mp"] = opcoes_mp[0]
    tipo_mp = st.selectbox("Como a Matéria-Prima será contabilizada?", opcoes_mp, key="sel_tipo_mp")
    
    custo_total_material = 0.0
    total_quilos = 0.0
    preco_unitario_mp = 0.0
    detalhes_material = ""
    material_sel, diametro, di_ext, di_int = "N/A", 0.0, 0.0, 0.0

    if tipo_mp == "Fornecido pelo Cliente (Mão de Obra Pura)":
        total_quilos = st.number_input("Peso total estimado do lote enviado pelo cliente (kg) [Essencial caso haja tratamento]", min_value=0.0, step=0.1, key="num_peso_fornecido")
        custo_total_material = 0.0
        preco_unitario_mp = 0.0
        detalhes_material = "Fornecido pelo Cliente"
        st.info("ℹ️ Material fornecido pelo parceiro. Campo de Preço por KG ocultado. Custo de Matéria-Prima definido como R$ 0,00.")
    else:
        col_mat1, col_mat2, col_mat3 = st.columns(3)
        with col_mat1:
            preco_unitario_mp = st.number_input("Preço Atual da MP (R$ por Kg, Metro ou Peça)", min_value=0.0, step=1.0, key="num_preco_mp")

        if "Por Peso" in tipo_mp:
            with col_mat2:
                opcoes_liga = list(DADOS_MATERIAIS.keys())
                if st.session_state["sel_liga"] not in opcoes_liga: st.session_state["sel_liga"] = opcoes_liga[0]
                material_sel = st.selectbox("Selecione a Liga (Constante)", opcoes_liga, key="sel_liga")
                constante = DADOS_MATERIAIS[material_sel]
            
            if tipo_mp == "Por Peso (Barra Maciça/Sextavada)":
                with col_mat3:
                    diametro = st.number_input("Diâmetro da Barra (mm)", min_value=0.0, step=0.1, key="num_diam_barra")
                peso_por_metro = (diametro ** 2 * constante) / 100
            else:
                with col_mat3:
                    di_ext = st.number_input("Diâmetro Externo (mm)", min_value=0.0, step=0.1, key="num_di_ext")
                    di_int = st.number_input("Diâmetro Interno/Furo (mm)", min_value=0.0, step=0.1, key="num_di_int")
                peso_por_metro = ((di_ext ** 2) - (di_int ** 2)) * constante / 100

            total_metros = ((comprimento + margem_corte) * lote) / 1000
            total_quilos = total_metros * peso_por_metro
            custo_total_material = total_quilos * preco_unitario_mp
            detalhes_material = f"{total_quilos:.2f} kg de {material_sel}"

        elif tipo_mp == "Por Metro Linear":
            total_metros = ((comprimento + margem_corte) * lote) / 1000
            custo_total_material = total_metros * preco_unitario_mp
            detalhes_material = f"{total_metros:.2f} m"
            with col_mat2:
                total_quilos = st.number_input("Peso total do lote (kg) [Para cálculo do Tratamento]", min_value=0.0, step=0.1, key="num_peso_metro")

        elif tipo_mp == "Por Peça Pronta":
            custo_total_material = lote * preco_unitario_mp
            detalhes_material = f"{lote} Peças base"
            with col_mat2:
                total_quilos = st.number_input("Peso total do lote (kg) [Para cálculo do Tratamento]", min_value=0.0, step=0.1, key="num_peso_peca")

    st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}", help=f"Peso total considerado: {total_quilos:.2f} kg")
    st.markdown("---")

    # --- BLOCO 4: PROCESSOS DE USINAGEM ---
    st.subheader("🔨 Roteiro de Processos de Usinagem")
    df_usinagem_input = st.data_editor(
        st.session_state["df_usinagem_v3"],
        num_rows="dynamic",
        column_config={
            "Operação": st.column_config.TextColumn("Operação", required=True),
            "Máquina": st.column_config.SelectboxColumn("Máquina", options=list(valores_maquinas.keys()), required=True),
            "Peças por Hora": st.column_config.NumberColumn("Produção (Pç/h)", min_value=1, default=50, required=True)
        },
        use_container_width=True,
        key="editor_usinagem_aba1"
    )
    st.session_state["df_usinagem_v3"] = df_usinagem_input

    custo_total_usinagem = 0.0
    for idx, row in df_usinagem_input.iterrows():
        try: custo_total_usinagem += (lote / row["Peças por Hora"]) * valores_maquinas.get(row["Máquina"], 120.0)
        except: pass

    st.caption(f"💰 Custo de Usinagem: **R$ {custo_total_usinagem:.2f}**")
    st.markdown("---")

    # --- BLOCO 5: TRATAMENTOS SUPERFICIAIS ---
    st.subheader("✨ Tratamentos Superficiais (Preço por KG)")
    df_trat_input = st.data_editor(
        st.session_state["df_tratamento_v3"],
        num_rows="dynamic",
        column_config={
            "Tratamento": st.column_config.TextColumn("Tratamento", required=True),
            "Preço por Kg (R$)": st.column_config.NumberColumn("Valor por Kg (R$)", min_value=0.0, default=0.0)
        },
        use_container_width=True,
        key="editor_tratamentos_aba1"
    )
    st.session_state["df_tratamento_v3"] = df_trat_input

    soma_preco_kg_tratamento = 0.0
    for idx, row in df_trat_input.iterrows():
        try: soma_preco_kg_tratamento += row["Preço por Kg (R$)"]
        except: pass
    custo_total_tratamentos = soma_preco_kg_tratamento * total_quilos
    st.caption(f"✨ Custo total de tratamento: **R$ {custo_total_tratamentos:.2f}**")
    st.markdown("---")

    # --- BLOCO 6: LUCRO E FECHAMENTO ---
    st.subheader("📈 Margem de Lucro e Fechamento")
    porcentagem_lucro = st.slider("Selecione a Margem de Lucro desejada (%)", min_value=15, max_value=95, step=5, key="slider_lucro_aba1")

    custo_bruto_total = custo_total_material + custo_total_usinagem + custo_total_tratamentos
    valor_com_lucro = custo_bruto_total / (1 - (porcentagem_lucro / 100))
    lucro_bruto_real = valor_com_lucro - custo_bruto_total
    total_imposto_pct = impostos["IR"] + impostos["FS"]
    valor_impostos = valor_com_lucro * (total_imposto_pct / 100)
    preco_venda_lote = valor_com_lucro + valor_impostos
    preco_unitario_final = preco_venda_lote / lote if lote > 0 else 0.0

    st.markdown("### 📋 Resumo da Proposta Atual")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo Total de Fábrica", f"R$ {custo_bruto_total:.2f}")
    c2.metric(f"Lucro Bruto Real", f"R$ {lucro_bruto_real:.2f}")
    c3.metric(f"Impostos ({total_imposto_pct}%)", f"R$ {valor_impostos:.2f}")
    c4.metric("Preço UNITÁRIO Final", f"R$ {preco_unitario_final:.2f}")

    # CORREÇÃO DA GRAVAÇÃO: Variáveis unificadas para evitar NameError
    if st.button("💾 Gravar no Histórico", type="primary", key="btn_salvar_aba1"):
        if not codigo_peca or codigo_peca == "➕ Novo Código...":
            st.error("Por favor, preencha o código da peça antes de salvar!")
        else:
            usinagem_json_str = df_usinagem_input.to_json(orient='records')
            tratamento_json_str = df_trat_input.to_json(orient='records') # CORRIGIDO: Nome sem erros de digitação
            
            novo_registro = {
                "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Origem/Alteração": "Novo Orçamento",
                "Código da Peça": codigo_peca,
                "Nome da Peça": nome_peca if nome_peca else "N/A",
                "Empresa": empresa if empresa else "N/A",
                "Comprador": comprador if comprador else "N/A",
                "Lote": lote,
                "Comprimento (mm)": comprimento,
                "Margem Corte (mm)": margem_corte,
                "Tipo MP": tipo_mp,
                "Preço MP Unitário": preco_unitario_mp,
                "Liga": material_sel,
                "Diâmetro (mm)": diametro,
                "Diâmetro Externo (mm)": di_ext,
                "Diâmetro Interno (mm)": di_int,
                "Total Kg Lote": round(total_quilos, 3),
                "Custo Material (R$)": round(custo_total_material, 2),
                "Custo Tratamento (R$)": round(custo_total_tratamentos, 2),
                "Margem Lucro (%)": porcentagem_lucro,
                "Preço Total Lote (R$)": round(preco_venda_lote, 2),
                "Preço Unitário (R$)": round(preco_unitario_final, 2),
                "Usinagem_JSON": usinagem_json_str,
                "Tratamento_JSON": tratamento_json_str # CORRIGIDO
            }
            df_novo = pd.DataFrame([novo_registro])
            if os.path.exists(ARQUIVO_HISTORICO):
                df_hist = pd.read_csv(ARQUIVO_HISTORICO)
                df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
            else:
                df_hist = df_novo
            df_hist.to_csv(ARQUIVO_HISTORICO, index=False)
            
            # Garante que a mensagem de sucesso persista na tela após recarregar
            st.session_state.mensagem_sucesso = f"✅ Sucesso! O orçamento do código '{codigo_peca}' foi gravado permanentemente!"
            st.session_state["dados_carregados"] = {} 
            st.rerun()

# =============================================================================
# TELA 2: HISTÓRICO & PREÇOS ATUAIS
# =============================================================================
elif opcao_menu == "📜 2. Histórico & Preços Atuais":
    st.subheader("📜 Histórico e Banco de Preços")
    if not os.path.exists(ARQUIVO_HISTORICO):
        st.info("Nenhum orçamento gerado ainda no sistema.")
    else:
        df_completo = pd.read_csv(ARQUIVO_HISTORICO)
        
        if "Origem/Alteração" not in df_completo.columns:
            df_completo["Origem/Alteração"] = "Novo Orçamento"
            
        clientes_existentes = sorted(df_completo["Empresa"].dropna().unique().tolist())
        cliente_filtro = st.multiselect("🔍 Filtrar visualização por Cliente/Empresa:", options=clientes_existentes, placeholder="Exibindo todos os clientes")
        
        opcao_visao = st.radio("Selecione a visualização dos dados:", ["🎯 Preços Atuais (Última Versão por Peça)", "⏳ Histórico de Alterações Completo"], key="rad_visao_aba2")
        
        df_base_filtrada = df_completo.copy()
        if cliente_filtro:
            df_base_filtrada = df_base_filtrada[df_base_filtrada["Empresa"].isin(cliente_filtro)]

        # TABELA LIMPA: Esconde as colunas brutas de JSON ilegíveis
        colunas_comerciais = [
            "Data/Hora", "Origem/Alteração", "Empresa", "Código da Peça", 
            "Nome da Peça", "Lote", "Preço Unitário (R$)", "Preço Total Lote (R$)"
        ]
        
        if opcao_visao == "⏳ Histórico de Alterações Completo":
            st.subheader("📋 Registro Cronológico Completo (Limpo)")
            st.dataframe(df_base_filtrada[colunas_comerciais].iloc[::-1], use_container_width=True)
        else:
            st.subheader("🎯 Tabela de Preços Atuais (Última versão de cada código)")
            df_ultimos_precos = df_completo.sort_values("Data/Hora").groupby("Código da Peça").last().reset_index()
            df_ultimos_precos = df_ultimos_precos.sort_values(by="Empresa")
            
            if cliente_filtro:
                df_ultimos_precos = df_ultimos_precos[df_ultimos_precos["Empresa"].isin(cliente_filtro)]
                
            st.dataframe(df_ultimos_precos[[
                "Empresa", "Código da Peça", "Nome da Peça", "Lote", 
                "Preço Unitário (R$)", "Preço Total Lote (R$)"
            ]], use_container_width=True)

# =============================================================================
# TELA 3: CONFIGURAÇÕES DE CUSTOS & RECÁLCULO EM MASSA
# =============================================================================
elif opcao_menu == "⚙️ 3. Configurações de Custos e Impostos":
    st.subheader("⚙️ Painel de Controle de Custos Fixos")
    col_cfg1, col_cfg2 = st.columns(2)
    
    with col_cfg1:
        st.markdown("#### 💰 Preço da Hora-Máquina (R$/hora)")
        maquinas_atualizadas = {}
        for maq, valor_padrao in st.session_state.valores_maquinas.items():
            maquinas_atualizadas[maq] = st.number_input(f"Taxa: {maq}", min_value=0.0, value=valor_padrao, step=5.0, key=f"cfg_maq_{maq}")
        st.session_state.valores_maquinas = maquinas_atualizadas

    with col_cfg2:
        st.markdown("#### 📝 Alíquotas de Impostos (%)")
        ir_atual = st.number_input("Imposto de Renda / Simples Base (%)", min_value=0.0, value=st.session_state.impostos["IR"], step=0.5, key="cfg_tax_ir")
        fs_atual = st.number_input("Fundo Social / Encargos (%)", min_value=0.0, value=st.session_state.impostos["FS"], step=0.5, key="cfg_tax_fs")
        st.session_state.impostos = {"IR": ir_atual, "FS": fs_atual}

    # FUNÇÃO DO RECÁLCULO GERAL: Processa as atualizações e salva permanentemente no CSV
    def processar_e_salvar_recalculo(dataframe_base):
        linhas_recalculadas = []
        novas_linhas_historico = []
        
        for _, row in dataframe_base.iterrows():
            try:
                roteiro = json.loads(row["Usinagem_JSON"])
                novo_custo_usinagem = 0.0
                for op in roteiro:
                    novo_custo_usinagem += (row["Lote"] / op["Peças por Hora"]) * valores_maquinas.get(op["Máquina"], 120.0)
                
                c_material = row["Custo Material (R$)"]
                c_tratamento = row["Custo Tratamento (R$)"]
                custo_fabrica_novo = c_material + novo_custo_usinagem + c_tratamento
                
                valor_lucro_novo = custo_fabrica_novo / (1 - (row["Margem Lucro (%)"] / 100))
                total_imp_pct = impostos["IR"] + impostos["FS"]
                preco_lote_novo = valor_lucro_novo + (valor_lucro_novo * (total_imp_pct / 100))
                preco_unit_novo = preco_lote_novo / row["Lote"]
                
                # Gera a visualização limpa para a tela
                linhas_recalculadas.append({
                    "Empresa/Cliente": row["Empresa"],
                    "Código da Peça": row["Código da Peça"],
                    "Nome da Peça": row["Nome da Peça"],
                    "Lote": row["Lote"],
                    "Novo Custo Usinagem (R$)": round(novo_custo_usinagem, 2),
                    "NOVO Preço Total Lote (R$)": round(preco_lote_novo, 2),
                    "NOVO Preço Unitário (R$)": round(preco_unit_novo, 2)
                })
                
                # Monta a nova linha estruturada que irá indexar o histórico permanentemente
                registro_recalculado_completo = row.to_dict()
                registro_recalculado_completo["Data/Hora"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                registro_recalculado_completo["Origem/Alteração"] = "Recálculo de Tarifas"
                registro_recalculado_completo["Preço Total Lote (R$)"] = round(preco_lote_novo, 2)
                registro_recalculado_completo["Preço Unitário (R$)"] = round(preco_unit_novo, 2)
                novas_linhas_historico.append(registro_recalculado_completo)
            except: 
                pass
                
        # Gravação em lote no arquivo de histórico CSV
        if novas_linhas_historico:
            df_novos_recalc = pd.DataFrame(novas_linhas_historico)
            if os.path.exists(ARQUIVO_HISTORICO):
                df_completo_atual = pd.read_csv(ARQUIVO_HISTORICO)
                df_final_salvar = pd.concat([df_completo_atual, df_novos_recalc], ignore_index=True)
            else:
                df_final_salvar = df_novos_recalc
            df_final_salvar.to_csv(ARQUIVO_HISTORICO, index=False)
            
        return pd.DataFrame(linhas_recalculadas)

    st.markdown("---")
    st.markdown("### 🍒 Recálculo Geral em Massa (Com gravação automática)")
    st.write("Selecione abaixo para quais clientes deseja disparar o recálculo. O sistema irá computar as novas taxas horárias e salvar automaticamente como uma nova revisão histórica.")
    
    if os.path.exists(ARQUIVO_HISTORICO):
        df_recalc_base = pd.read_csv(ARQUIVO_HISTORICO)
        clientes_para_recalc = sorted(df_recalc_base["Empresa"].dropna().unique().tolist())
        
        clientes_selecionados = st.multiselect("Selecione os Clientes para Recalcular:", options=clientes_para_recalc, placeholder="Deixe vazio para recalcular TODOS os clientes", key="multiselect_recalc_aba3")
        
        if st.button("🔄 Executar Recálculo de Tarifas e Salvar", type="primary", key="btn_recalc_aba3"):
            df_ultimos_recalc = df_recalc_base.sort_values("Data/Hora").groupby("Código da Peça").last().reset_index()
            
            if clientes_selecionados:
                df_ultimos_recalc = df_ultimos_recalc[df_ultimos_recalc["Empresa"].isin(clientes_selecionados)]
                
            df_atualizado = processar_e_salvar_recalculo(df_ultimos_recalc)
            if not df_atualizado.empty:
                st.session_state.mensagem_sucesso = "🚀 Sucesso! Todas as peças da seleção foram recalculadas com as novas taxas e salvas como novas revisões no histórico!"
                st.dataframe(df_atualizado, use_container_width=True)
                
                csv_export = df_atualizado.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Tabela Recalculada (Excel/CSV)", data=csv_export, file_name="precos_recalculados_usinagem.csv", mime="text/csv", key="btn_dl_csv_aba3")
                st.rerun()
            else:
                st.warning("Nenhum roteiro válido encontrado para processar.")
    else:
        st.info("Gere alguns orçamentos primeiro para liberar o recálculo em massa.")
