import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# 1. CONFIGURAÇÕES INICIAIS DA PÁGINA (Sempre no topo)
st.set_page_config(page_title="Orçamentos Lenoor V2", page_icon="⚙️", layout="wide")

# Nome do arquivo de banco de dados local
ARQUIVO_HISTORICO = "historico_orcamentos_estruturado.csv"

# Constantes fixas de materiais
DADOS_MATERIAIS = {
    "aço sx": 0.68, "aço red": 0.62, "aço quad": 0.72,
    "aluminio red": 0.212, "aluminio quad": 0.212, "aluminio sx": 0.212,
    "latao red": 0.68, "latao quad": 0.78, "latao sx": 0.72
}

# 2. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO (Garante estabilidade dos dados)
if "valores_maquinas" not in st.session_state:
    st.session_state.valores_maquinas = {
        "CNC": 150.0, "Torno Automático": 120.0, "Freza": 120.0,
        "Furadeira": 70.0, "Torno Revolver": 90.0, "Retífica": 150.0,
        "Serra": 70.0, "Montagem": 90.0, "Outro": 150.0
    }
if "impostos" not in st.session_state:
    st.session_state.impostos = {"IR": 6.0, "FS": 4.0}
if "dados_carregados" not in st.session_state:
    st.session_state.dados_carregados = None

# Atalhos para os valores atuais configurados
valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos

st.title("Sistema Orçamentos Lenoor")

# 3. CRIAÇÃO DAS ABAS NA TELA
aba_calculo, aba_historico, aba_config = st.tabs([
    "📊 1. Novo Orçamento", 
    "📜 2. Histórico & Preços Atuais", 
    "⚙️ 3. Configurações de Custos e Impostos"
])

# =============================================================================
# ABA 1: NOVO ORÇAMENTO (Tudo isolado aqui dentro)
# =============================================================================
with aba_calculo:
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    with col_cli1:
        empresa = st.text_input("Empresa/Cliente", value="", placeholder="Ex: TS", key="txt_empresa")
    with col_cli2:
        comprador = st.text_input("Comprador Responsável", value="", placeholder="Ex: Guilherme", key="txt_comprador")

    st.markdown("---")
    
    st.subheader("📦 Dados do Produto")
    col_prod1, col_prod2, col_prod3 = st.columns(3)
    
    with col_prod1:
        codigo_peca = st.text_input("Código da Peça", value="", placeholder="Ex: TS-8-030-XXXX", key="txt_codigo")
        
        # Busca por histórico anterior
        if codigo_peca and os.path.exists(ARQUIVO_HISTORICO):
            df_hist_busca = pd.read_csv(ARQUIVO_HISTORICO)
            df_filtrado = df_hist_busca[df_hist_busca["Código da Peça"] == codigo_peca]
            if not df_filtrado.empty:
                st.info(f"🔍 Cotação anterior encontrada para o código {codigo_peca}!")
                if st.button("🔄 Carregar dados da última versão", key="btn_carregar_hist"):
                    st.session_state.dados_carregados = df_filtrado.iloc[-1].to_dict()
                    st.rerun()

    # Recupera dados se o usuário aceitou carregar o histórico
    hist = st.session_state.dados_carregados if st.session_state.dados_carregados else {}
    
    with col_prod2:
        nome_peca = st.text_input("Nome da Peça", value=hist.get("Nome da Peça", ""), key="txt_nome_peca")
    with col_prod3:
        lote = st.number_input("Quantidade do Lote", min_value=1, value=int(hist.get("Lote", 100)), key="num_lote")

    col_prod4, col_prod5 = st.columns(2)
    with col_prod4:
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, value=float(hist.get("Comprimento (mm)", 0.0)), key="num_comprimento")
    with col_prod5:
        margem_corte = st.number_input("Margem de Corte/Perda por peça (mm)", min_value=0.0, value=5.0, key="num_margem_corte")

    st.markdown("---")

    st.subheader("🧱 Definição da Matéria-Prima")
    tipo_mp = st.selectbox("Como a Matéria-Prima será contabilizada?", 
                           ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Fornecido pelo Cliente (Mão de Obra Pura)"],
                           key="sel_tipo_mp")
    
    custo_total_material = 0.0
    total_quilos = 0.0
    detalhes_material = ""

    col_mat1, col_mat2, col_mat3 = st.columns(3)
    with col_mat1:
        preco_unitario_mp = st.number_input("Preço Atual da MP (R$ por Kg, Metro ou Peça)", min_value=0.0, value=float(hist.get("Preço MP Unitário", 0.0)) if hist else 0.0, step=1.0, key="num_preco_mp")

    if "Por Peso" in tipo_mp:
        with col_mat2:
            material_sel = st.selectbox("Selecione a Liga (Constante)", list(DADOS_MATERIAIS.keys()), key="sel_liga")
            constante = DADOS_MATERIAIS[material_sel]
        
        if tipo_mp == "Por Peso (Barra Maciça/Sextavada)":
            with col_mat3:
                diametro = st.number_input("Diâmetro da Barra (mm)", min_value=0.0, value=15.0, key="num_diam_barra")
            peso_por_metro = (diametro ** 2 * constante) / 100
        else:
            with col_mat3:
                di_ext = st.number_input("Diâmetro Externo (mm)", min_value=0.0, value=20.0, key="num_di_ext")
                di_int = st.number_input("Diâmetro Interno/Furo (mm)", min_value=0.0, value=10.0, key="num_di_int")
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
            total_quilos = st.number_input("Peso total do lote (kg) [Para cálculo do Tratamento]", min_value=0.1, value=10.0, key="num_peso_metro")

    elif tipo_mp == "Por Peça Pronta" or "Fornecido" in tipo_mp:
        custo_total_material = 0.0 if "Fornecido" in tipo_mp else (lote * preco_unitario_mp)
        detalhes_material = "Fornecido pelo Cliente" if "Fornecido" in tipo_mp else f"{lote} Peças base"
        with col_mat2:
            total_quilos = st.number_input("Peso total do lote (kg) [Para cálculo do Tratamento]", min_value=0.1, value=10.0, key="num_peso_peca")

    st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}", help=f"Peso total considerado: {total_quilos:.2f} kg")
    st.markdown("---")

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

    st.subheader("✨ Tratamentos Superficiais (Preço por KG)")
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

    st.subheader("📈 Margem de Lucro e Fechamento")
    porcentagem_lucro = st.slider("Selecione a Margem de Lucro desejada (%)", min_value=15, max_value=95, value=30, step=5, key="slider_lucro_aba1")

    # Cálculos Matemáticos Finais (Regra Tradicional do seu pai)
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
        novo_registro = {
            "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Código da Peça": codigo_peca if codigo_peca else "N/A",
            "Nome da Peça": nome_peca if nome_peca else "N/A",
            "Empresa": empresa if empresa else "N/A",
            "Comprador": comprador if comprador else "N/A",
            "Lote": lote,
            "Comprimento (mm)": comprimento,
            "Tipo MP": tipo_mp,
            "Preço MP Unitário": preco_unitario_mp,
            "Total Kg Lote": round(total_quilos, 3),
            "Custo Material (R$)": round(custo_total_material, 2),
            "Custo Tratamento (R$)": round(custo_total_tratamentos, 2),
            "Margem Lucro (%)": porcentagem_lucro,
            "Usinagem_JSON": usinagem_json_str
        }
        df_novo = pd.DataFrame([novo_registro])
        if os.path.exists(ARQUIVO_HISTORICO):
            df_hist = pd.read_csv(ARQUIVO_HISTORICO)
            df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
        else:
            df_hist = df_novo
        df_hist.to_csv(ARQUIVO_HISTORICO, index=False)
        st.success("✅ Cotação salva com sucesso!")
        st.session_state.dados_carregados = None

# =============================================================================
# ABA 2: HISTÓRICO & RECÁLCULO EM MASSA
# =============================================================================
with aba_historico:
    st.subheader("📜 Histórico e Banco de Preços")
    if not os.path.exists(ARQUIVO_HISTORICO):
        st.info("Nenhum orçamento gerado ainda no sistema.")
    else:
        df_completo = pd.read_csv(ARQUIVO_HISTORICO)
        opcao_visao = st.radio("Selecione a visualização dos dados:", ["🎯 Preços Atuais (Última Versão por Peça/Empresa)", "⏳ Histórico de Alterações Completo"], key="rad_visao_aba2")
        
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
                    impostos_novos = valor_lucro_novo * (total_imp_pct / 100)
                    preco_lote_novo = valor_lucro_novo + impostos_novos
                    linhas_recalculadas.append({
                        "Empresa/Cliente": row["Empresa"],
                        "Código da Peça": row["Código da Peça"],
                        "Nome da Peça": row["Nome da Peça"],
                        "Lote": row["Lote"],
                        "Custo Mat. Prima (R$)": c_material,
                        "Novo Custo Usinagem (R$)": round(novo_custo_usinagem, 2),
                        "Custo Tratamento (R$)": c_tratamento,
                        "NOVO Preço Total Lote (R$)": round(preco_lote_novo, 2),
                        "NOVO Preço Unitário (R$)": round(preco_lote_novo / row["Lote"], 2)
                    })
                except: pass
            return pd.DataFrame(linhas_recalculadas)

        if opcao_visao == "⏳ Histórico de Alterações Completo":
            st.subheader("📋 Registro Cronológico Completo")
            st.dataframe(df_completo.iloc[::-1], use_container_width=True)
        else:
            st.subheader("🎯 Tabela de Preços Atuais (Organizado por Empresa)")
            df_ultimos_precos = df_completo.sort_values("Data/Hora").groupby("Código da Peça").last().reset_index()
            df_ultimos_precos = df_ultimos_precos.sort_values(by="Empresa")
            st.dataframe(df_ultimos_precos[["Empresa", "Código da Peça", "Nome da Peça", "Lote", "Custo Material (R$)", "Custo Tratamento (R$)"]], use_container_width=True)
            
            st.markdown("### 🍒 Recálculo Geral em Massa")
            st.write("Clique no botão abaixo para aplicar as novas taxas de máquinas/impostos da Aba 3 em todos os clientes cadastrados simultaneamente:")
            if st.button("🔄 Recalcular Todos os Preços Atuais", type="primary", key="btn_recalc_aba2"):
                df_atualizado = processar_recalculo(df_ultimos_precos)
                if not df_atualizado.empty:
                    st.success("🚀 Preços recalculados com sucesso!")
                    st.dataframe(df_atualizado, use_container_width=True)
                    csv_export = df_atualizado.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Tabela Atualizada (Excel/CSV)", data=csv_export, file_name="precos_atualizados_usinagem.csv", mime="text/csv", key="btn_dl_csv")

# =============================================================================
# ABA 3: CONFIGURAÇÕES DE CUSTOS E IMPOSTOS
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
        st.caption("ℹ️ Mudanças aqui afetam automaticamente novos orçamentos e a ferramenta de recálculo em massa.")
