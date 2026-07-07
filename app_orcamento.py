import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# 1. CONFIGURAÇÕES INICIAIS DA PÁGINA
st.set_page_config(page_title="Sistema Lenoor Orçamentos v3", page_icon="⚙️", layout="wide")

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

# Carrega listas do histórico para sugestão automática (Autocomplete)
lista_empresas = []
lista_codigos = []
if os.path.exists(ARQUIVO_HISTORICO):
    try:
        df_init = pd.read_csv(ARQUIVO_HISTORICO)
        lista_empresas = sorted(df_init["Empresa"].dropna().unique().tolist())
        lista_codigos = sorted(df_init["Código da Peça"].dropna().unique().tolist())
    except:
        pass

# Atalhos para as configurações atuais
valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos

st.title("Sistema Lenoor de Orçamentos")

# 3. CRIAÇÃO DAS ABAS NA TELA
aba_calculo, aba_historico, aba_config = st.tabs([
    "📊 1. Novo Orçamento", 
    "📜 2. Histórico & Preços Atuais", 
    "⚙️ 3. Configurações de Custos e Impostos"
])

# =============================================================================
# ABA 1: NOVO ORÇAMENTO
# =============================================================================
with aba_calculo:
    # --- BLOCO 1: DADOS DO CLIENTE (DE VOLTA AO TOPO!) ---
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    
    hist = st.session_state.dados_carregados
    
    with col_cli1:
        # Autocomplete de empresas baseado no histórico
        default_empresa = hist.get("Empresa", "")
        idx_empresa = lista_empresas.index(default_empresa) + 1 if default_empresa in lista_empresas else 0
        
        empresa_sel = st.selectbox("Empresa/Cliente", [""] + lista_empresas + ["➕ Novo Cliente..."], index=idx_empresa, key="sel_empresa_aba1")
        if empresa_sel == "➕ Novo Cliente...":
            empresa = st.text_input("Digite o nome do Novo Cliente", placeholder="Ex: TS")
        else:
            empresa = empresa_sel
            
    with col_cli2:
        comprador = st.text_input("Comprador Responsável", value=hist.get("Comprador", ""), placeholder="Ex: Guilherme", key="txt_comprador")

    st.markdown("---")
    
    # --- BLOCO 2: DADOS DO PRODUTO + BOTÃO DE AUTOCOMPLETAR ---
    st.subheader("📦 Dados do Produto")
    col_prod1, col_prod2, col_prod3 = st.columns(3)
    
    with col_prod1:
        # Autocomplete de códigos baseado no histórico
        default_codigo = hist.get("Código da Peça", "")
        idx_codigo = lista_codigos.index(default_codigo) + 1 if default_codigo in lista_codigos else 0
        
        codigo_sel = st.selectbox("Código da Peça", [""] + lista_codigos + ["➕ Novo Código..."], index=idx_codigo, key="sel_codigo_peca")
        if codigo_sel == "➕ Novo Código...":
            codigo_peca = st.text_input("Digite o Novo Código", placeholder="Ex: TS-8-030-XXXX")
        else:
            codigo_peca = codigo_sel

    with col_prod2:
        nome_peca = st.text_input("Nome da Peça", value=hist.get("Nome da Peça", ""), key="txt_nome_peca")
    with col_prod3:
        lote = st.number_input("Quantidade do Lote", min_value=1, value=int(hist.get("Lote", 100)), key="num_lote")

    col_prod4, col_prod5 = st.columns(2)
    with col_prod4:
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, value=float(hist.get("Comprimento (mm)", 0.0)), key="num_comprimento")
    with col_prod5:
        margem_corte = st.number_input("Margem de Corte/Perda por peça (mm)", min_value=0.0, value=float(hist.get("Margem Corte (mm)", 5.0)), key="num_margem_corte")

    # BOTÃO PEDIDO: Só completa se o usuário clicar explicitamente nele
    if codigo_sel and codigo_sel != "➕ Novo Código..." and os.path.exists(ARQUIVO_HISTORICO):
        if st.button("📋 Completar Dados com Roteiro Antigo", type="secondary", use_container_width=True):
            try:
                df_hist_busca = pd.read_csv(ARQUIVO_HISTORICO)
                df_filtrado = df_hist_busca[df_hist_busca["Código da Peça"] == codigo_sel]
                if not df_filtrado.empty:
                    st.session_state.dados_carregados = df_filtrado.iloc[-1].to_dict()
                    st.success("⚡ Todos os campos, roteiros e lucros foram preenchidos!")
                    st.rerun()
            except:
                pass

    st.markdown("---")

    # --- BLOCO 3: MATÉRIA-PRIMA ---
    st.subheader("🧱 Definição da Matéria-Prima")
    opcoes_mp = ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Fornecido pelo Cliente (Mão de Obra Pura)"]
    idx_mp = opcoes_mp.index(hist["Tipo MP"]) if "Tipo MP" in hist and hist["Tipo MP"] in opcoes_mp else 0
    tipo_mp = st.selectbox("Como a Matéria-Prima será contabilizada?", opcoes_mp, index=idx_mp, key="sel_tipo_mp")
    
    custo_total_material = 0.0
    total_quilos = 0.0
    detalhes_material = ""

    col_mat1, col_mat2, col_mat3 = st.columns(3)
    with col_mat1:
        preco_unitario_mp = st.number_input("Preço Atual da MP (R$ por Kg, Metro ou Peça)", min_value=0.0, value=float(hist.get("Preço MP Unitário", 0.0)), step=1.0, key="num_preco_mp")

    if "Por Peso" in tipo_mp:
        with col_mat2:
            opcoes_liga = list(DADOS_MATERIAIS.keys())
            idx_liga = opcoes_liga.index(hist["Liga"]) if "Liga" in hist and hist["Liga"] in opcoes_liga else 0
            material_sel = st.selectbox("Selecione a Liga (Constante)", opcoes_liga, index=idx_liga, key="sel_liga")
            constante = DADOS_MATERIAIS[material_sel]
        
        if tipo_mp == "Por Peso (Barra Maciça/Sextavada)":
            with col_mat3:
                diametro = st.number_input("Diâmetro da Barra (mm)", min_value=0.0, value=float(hist.get("Diâmetro (mm)", 15.0)), key="num_diam_barra")
            peso_por_metro = (diametro ** 2 * constante) / 100
        else:
            with col_mat3:
                di_ext = st.number_input("Diâmetro Externo (mm)", min_value=0.0, value=float(hist.get("Diâmetro Externo (mm)", 20.0)), key="num_di_ext")
                di_int = st.number_input("Diâmetro Interno/Furo (mm)", min_value=0.0, value=float(hist.get("Diâmetro Interno (mm)", 10.0)), key="num_di_int")
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
            total_quilos = st.number_input("Peso total do lote (kg) [Para cálculo do Tratamento]", min_value=0.1, value=float(hist.get("Total Kg Lote", 10.0)), key="num_peso_metro")

    elif tipo_mp == "Por Peça Pronta" or "Fornecido" in tipo_mp:
        custo_total_material = 0.0 if "Fornecido" in tipo_mp else (lote * preco_unitario_mp)
        detalhes_material = "Fornecido pelo Cliente" if "Fornecido" in tipo_mp else f"{lote} Peças base"
        with col_mat2:
            total_quilos = st.number_input("Peso total do lote (kg) [Para cálculo do Tratamento]", min_value=0.1, value=float(hist.get("Total Kg Lote", 10.0)), key="num_peso_peca")

    st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}", help=f"Peso total considerado: {total_quilos:.2f} kg")
    st.markdown("---")

    # --- BLOCO 4: PROCESSOS DE USINAGEM ---
    st.subheader("🔨 Roteiro de Processos de Usinagem")
    if hist and "Usinagem_JSON" in hist:
        try: default_rows = json.loads(hist["Usinagem_JSON"])
        except: default_rows = [{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50}]
    else:
        default_rows = [{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50}]

    df_usinagem_input = st.data_editor(
        pd.DataFrame(default_rows),
        num_rows="dynamic",
        column_config={
            "Operação": st.column_config.TextColumn("Operação", required=True),
            "Máquina": st.column_config.SelectboxColumn("Máquina", options=list(valores_maquinas.keys()), required=True),
            "Peças por Hora": st.column_config.NumberColumn("Produção (Pç/h)", min_value=1, default=50, required=True)
        },
        use_container_width=True,
        key="editor_usinagem_aba1"
    )

    custo_total_usinagem = 0.0
    for idx, row in df_usinagem_input.iterrows():
        try: custo_total_usinagem += (lote / row["Peças por Hora"]) * valores_maquinas.get(row["Máquina"], 120.0)
        except: pass

    st.caption(f"💰 Custo de Usinagem: **R$ {custo_total_usinagem:.2f}**")
    st.markdown("---")

    # --- BLOCO 5: TRATAMENTOS SUPERFICIAIS ---
    st.subheader("✨ Tratamentos Superficiais (Preço por KG)")
    if hist and "Tratamento_JSON" in hist:
        try: default_trats = json.loads(hist["Tratamento_JSON"])
        except: default_trats = [{"Tratamento": "Nenhum / Sem Tratamento", "Preço por Kg (R$)": 0.0}]
    else:
        default_trats = [{"Tratamento": "Nenhum / Sem Tratamento", "Preço por Kg (R$)": 0.0}]

    df_trat_input = st.data_editor(
        pd.DataFrame(default_trats),
        num_rows="dynamic",
        column_config={
            "Tratamento": st.column_config.TextColumn("Tratamento", required=True),
            "Preço por Kg (R$)": st.column_config.NumberColumn("Valor por Kg (R$)", min_value=0.0, default=0.0)
        },
        use_container_width=True,
        key="editor_tratamentos_aba1"
    )

    soma_preco_kg_tratamento = 0.0
    for idx, row in df_trat_input.iterrows():
        try: soma_preco_kg_tratamento += row["Preço por Kg (R$)"]
        except: pass
    custo_total_tratamentos = soma_preco_kg_tratamento * total_quilos
    st.caption(f"✨ Custo total de tratamento: **R$ {custo_total_tratamentos:.2f}**")
    st.markdown("---")

    # --- BLOCO 6: LUCRO E FECHAMENTO ---
    st.subheader("📈 Margem de Lucro e Fechamento")
    default_lucro = int(hist.get("Margem Lucro (%)", 30))
    porcentagem_lucro = st.slider("Selecione a Margem de Lucro desejada (%)", min_value=15, max_value=95, value=default_lucro, step=5, key="slider_lucro_aba1")

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

    if st.button("💾 Gravar no Histórico", type="primary", key="btn_salvar_aba1"):
        usinagem_json_str = df_usinagem_input.to_json(orient='records')
        tratamento_json_str = df_trat_input.to_json(orient='records')
        
        novo_registro = {
            "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Código da Peça": codigo_peca if codigo_peca else "N/A",
            "Nome da Peça": nome_peca if nome_peca else "N/A",
            "Empresa": empresa if empresa else "N/A",
            "Comprador": comprador if comprador else "N/A",
            "Lote": lote,
            "Comprimento (mm)": comprimento,
            "Margem Corte (mm)": margem_corte,
            "Tipo MP": tipo_mp,
            "Preço MP Unitário": preco_unitario_mp,
            "Liga": material_sel if "Por Peso" in tipo_mp else "N/A",
            "Diâmetro (mm)": diametro if tipo_mp == "Por Peso (Barra Maciça/Sextavada)" else 0.0,
            "Diâmetro Externo (mm)": di_ext if tipo_mp == "Por Peso (Tubo/Bucha)" else 0.0,
            "Diâmetro Interno (mm)": di_int if tipo_mp == "Por Peso (Tubo/Bucha)" else 0.0,
            "Total Kg Lote": round(total_quilos, 3),
            "Custo Material (R$)": round(custo_total_material, 2),
            "Custo Tratamento (R$)": round(custo_total_tratamentos, 2),
            "Margem Lucro (%)": porcentagem_lucro,
            "Preço Total Lote (R$)": round(preco_venda_lote, 2),
            "Preço Unitário (R$)": round(preco_unitario_final, 2),
            "Usinagem_JSON": usinagem_json_str,
            "Tratamento_JSON": tratamento_json_str
        }
        df_novo = pd.DataFrame([novo_registro])
        if os.path.exists(ARQUIVO_HISTORICO):
            df_hist = pd.read_csv(ARQUIVO_HISTORICO)
            df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
        else:
            df_hist = df_novo
        df_hist.to_csv(ARQUIVO_HISTORICO, index=False)
        st.success("✅ Cotação salva com sucesso!")
        st.session_state.dados_carregados = {}  # Limpa o estado para o próximo
        st.rerun()

# =============================================================================
# ABA 2: HISTÓRICO & PREÇOS ATUAIS (Ponto 5 - Filtros Avançados)
# =============================================================================
with aba_historico:
    st.subheader("📜 Histórico e Banco de Preços")
    if not os.path.exists(ARQUIVO_HISTORICO):
        st.info("Nenhum orçamento gerado ainda no sistema.")
    else:
        df_completo = pd.read_csv(ARQUIVO_HISTORICO)
        
        # Ponto 5: Filtrar por cliente de forma explícita na Aba 2
        clientes_existentes = sorted(df_completo["Empresa"].dropna().unique().tolist())
        cliente_filtro = st.multiselect("🔍 Filtrar visualização por Cliente/Empresa:", options=clientes_existentes, placeholder="Exibindo todos os clientes")
        
        opcao_visao = st.radio("Selecione a visualização dos dados:", ["🎯 Preços Atuais (Última Versão por Peça)", "⏳ Histórico de Alterações Completo"], key="rad_visao_aba2")
        
        df_base_filtrada = df_completo.copy()
        if cliente_filtro:
            df_base_filtrada = df_base_filtrada[df_base_filtrada["Empresa"].isin(cliente_filtro)]

        if opcao_visao == "⏳ Histórico de Alterações Completo":
            st.subheader("📋 Registro Cronológico Completo")
            st.dataframe(df_base_filtrada.iloc[::-1], use_container_width=True)
        else:
            st.subheader("🎯 Tabela de Preços Atuais")
            df_ultimos_precos = df_completo.sort_values("Data/Hora").groupby("Código da Peça").last().reset_index()
            df_ultimos_precos = df_ultimos_precos.sort_values(by="Empresa")
            
            if cliente_filtro:
                df_ultimos_precos = df_ultimos_precos[df_ultimos_precos["Empresa"].isin(cliente_filtro)]
                
            st.dataframe(df_ultimos_precos[[
                "Empresa", "Código da Peça", "Nome da Peça", "Lote", 
                "Preço Unitário (R$)", "Preço Total Lote (R$)"
            ]], use_container_width=True)

# =============================================================================
# ABA 3: CONFIGURAÇÕES DE CUSTOS & RECÁLCULO EM MASSA (Ponto 4 - Centralizado)
# =============================================================================
with aba_config:
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

    # Função de recálculo
    def processar_recalculo(dataframe_base):
        linhas_recalculadas = []
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
                linhas_recalculadas.append({
                    "Empresa/Cliente": row["Empresa"],
                    "Código da Peça": row["Código da Peça"],
                    "Nome da Peça": row["Nome da Peça"],
                    "Lote": row["Lote"],
                    "Novo Custo Usinagem (R$)": round(novo_custo_usinagem, 2),
                    "NOVO Preço Total Lote (R$)": round(preco_lote_novo, 2),
                    "NOVO Preço Unitário (R$)": round(preco_lote_novo / row["Lote"], 2)
                })
            except: pass
        return pd.DataFrame(linhas_recalculadas)

    # Ponto 4: Ferramenta de recálculo em massa centralizada abaixo das configurações
    st.markdown("---")
    st.markdown("### 🍒 Recálculo Geral em Massa (Segmentado)")
    st.write("Deseja simular o impacto de novos preços de máquina em clientes específicos antes de salvar? Selecione abaixo:")
    
    if os.path.exists(ARQUIVO_HISTORICO):
        df_recalc_base = pd.read_csv(ARQUIVO_HISTORICO)
        clientes_para_recalc = sorted(df_recalc_base["Empresa"].dropna().unique().tolist())
        
        clientes_selecionados = st.multiselect("Selecione os Clientes para Recalcular:", options=clientes_para_recalc, placeholder="Deixe vazio para recalcular TODOS os clientes", key="multiselect_recalc_aba3")
        
        if st.button("🔄 Executar Recálculo de Tarifas", type="primary", key="btn_recalc_aba3"):
            df_ultimos_recalc = df_recalc_base.sort_values("Data/Hora").groupby("Código da Peça").last().reset_index()
            
            if clientes_selecionados:
                df_ultimos_recalc = df_ultimos_recalc[df_ultimos_recalc["Empresa"].isin(clientes_selecionados)]
                
            df_atualizado = processar_recalculo(df_ultimos_recalc)
            if not df_atualizado.empty:
                st.success(f"🚀 Preços simulados e recalculados com sucesso!")
                st.dataframe(df_atualizado, use_container_width=True)
                
                csv_export = df_atualizado.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Tabela Recalculada (Excel/CSV)", data=csv_export, file_name="precos_recalculados_usinagem.csv", mime="text/csv", key="btn_dl_csv_aba3")
            else:
                st.warning("Nenhum roteiro válido encontrado para processar.")
    else:
        st.info("Gere alguns orçamentos primeiro para liberar o recálculo em massa.")
