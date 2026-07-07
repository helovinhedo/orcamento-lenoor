import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import io

# =============================================================================
# 🧱 1. CONFIGURAÇÕES INICIAIS E FUNÇÕES UTILITÁRIAS DE SEGURANÇA
# =============================================================================
st.set_page_config(page_title="Sistema Lenoor - Orçamentos v3", page_icon="⚙️", layout="wide")

ARQUIVO_HISTORICO = "historico_orcamentos_estruturado.csv"
ARQUIVO_CONFIG = "config_lenoor.json"  

DADOS_MATERIAIS = {
    "aço sx": 0.68, "aço red": 0.62, "aço quad": 0.72,
    "aluminio red": 0.212, "aluminio quad": 0.212, "aluminio sx": 0.212,
    "latao red": 0.68, "latao quad": 0.78, "latao sx": 0.72
}

COLUNAS_PADRAO = [
    "Data/Hora", "Origem/Alteração", "Código da Peça", "Nome da Peça",
    "Empresa", "Comprador", "Lote", "Comprimento (mm)", "Margem Corte (mm)",
    "Tipo MP", "Preço MP Unitário", "Liga", "Diâmetro (mm)", "Diâmetro Externo (mm)",
    "Diâmetro Interno (mm)", "Total Kg Lote", "Custo Material (R$)", "Custo Tratamento (R$)",
    "Margem Lucro (%)", "Preço Total Lote (R$)", "Preço Unitário (R$)", "Usinagem_JSON", "Tratamento_JSON"
]

DEFAULTS_MAQUINAS = {
    "CNC": 150.0, "Torno Automático": 120.0, "Freza": 120.0,
    "Furadeira": 70.0, "Torno Revolver": 90.0, "Retífica": 150.0,
    "Serra": 70.0, "Montagem": 90.0, "Outro": 150.0
}
DEFAULTS_IMPOSTOS = {"IR": 6.0, "FS": 4.0}

# Funções de conversão segura (Anti-Crash)
def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or val is None: return default
        return float(val)
    except: return default

def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None: return default
        return int(float(val))
    except: return default

def safe_str(val, default=""):
    if pd.isna(val) or val is None: return default
    return str(val).strip()

# Leitura e Gravação Permanente de Configurações das Taxas Padrão
def ler_config_permanente():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r") as f:
                return json.load(f)
        except: pass
    return {"valores_maquinas": DEFAULTS_MAQUINAS, "impostos": DEFAULTS_IMPOSTOS}

def salvar_config_permanente(maquinas, impostos):
    try:
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump({"valores_maquinas": maquinas, "impostos": impostos}, f, indent=4)
    except Exception as e:
        st.error(f"Erro ao salvar arquivo de configurações: {e}")

def ler_historico_seguro():
    if not os.path.exists(ARQUIVO_HISTORICO):
        return pd.DataFrame(columns=COLUNAS_PADRAO)
    try:
        df = pd.read_csv(ARQUIVO_HISTORICO)
        for col in COLUNAS_PADRAO:
            if col not in df.columns: df[col] = None
        return df
    except Exception as e:
        st.error(f"⚠️ O arquivo de histórico está corrompido. Detalhes: {e}")
        return pd.DataFrame(columns=COLUNAS_PADRAO)

# =============================================================================
# 🧠 2. INICIALIZAÇÃO CONTROLADA DE VARIÁVEIS DE SESSÃO
# =============================================================================
config_carregada = ler_config_permanente()

if "valores_maquinas" not in st.session_state:
    st.session_state.valores_maquinas = config_carregada["valores_maquinas"]
if "impostos" not in st.session_state:
    st.session_state.impostos = config_carregada["impostos"]
if "dados_carregados" not in st.session_state:
    st.session_state.dados_carregados = {}
if "menu_anterior" not in st.session_state:
    st.session_state.menu_anterior = ""
if "df_recalculado_resultado" not in st.session_state:
    st.session_state["df_recalculado_resultado"] = None
if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0  
if "taxas_original_msg" not in st.session_state:
    st.session_state["taxas_original_msg"] = ""

# Inicialização de chaves de widgets (Margem padrão fixada em 5mm)
valores_padrao_widgets = {
    "sel_empresa_aba1": "", "txt_comprador": "", "sel_codigo_peca": "", "txt_nome_peca": "",
    "num_lote": 100, "num_comprimento": 0.0, "num_margem_corte": 5.0, 
    "sel_tipo_mp": "Por Peso (Barra Maciça/Sextavada)", "num_preco_mp": 0.0, "sel_liga": "aço sx",
    "num_diam_barra": 15.0, "num_di_ext": 20.0, "num_di_int": 10.0, "num_peso_metro": 10.0,
    "num_peso_peca": 10.0, "num_peso_fornecido": 0.0, "slider_lucro_aba1": 30
}
for chave, val in valores_padrao_widgets.items():
    if chave not in st.session_state: st.session_state[chave] = val

if "df_usinagem_v3" not in st.session_state:
    st.session_state["df_usinagem_v3"] = pd.DataFrame([{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50.0}])
if "df_tratamento_v3" not in st.session_state:
    st.session_state["df_tratamento_v3"] = pd.DataFrame([{"Tratamento": "Nenhum / Sem Tratamento", "Preço por Kg (R$)": 0.0}])

# Carga de listas adaptadas do histórico (Filtro Inteligente de Códigos por Cliente)
lista_empresas = []
lista_codigos = []
df_init = ler_historico_seguro()

if not df_init.empty:
    lista_empresas = sorted(df_init["Empresa"].dropna().astype(str).unique().tolist())
    empresa_atual = st.session_state.get("sel_empresa_aba1", "")
    if empresa_atual and empresa_atual != "➕ Novo Cliente...":
        df_filtrado_cod = df_init[df_init["Empresa"] == empresa_atual]
        lista_codigos = sorted(df_filtrado_cod["Código da Peça"].dropna().astype(str).unique().tolist())
    else:
        lista_codigos = sorted(df_init["Código da Peça"].dropna().astype(str).unique().tolist())

# --- FUNÇÃO DE CALLBACK PARA AUTOCOMPLETE SEGURO ---
def carregar_roteiro_antigo_callback():
    codigo_target = st.session_state.get("sel_codigo_peca", "")
    if codigo_target and codigo_target != "➕ Novo Código...":
        try:
            df_hist_busca = ler_historico_seguro()
            df_filtrado = df_hist_busca[df_hist_busca["Código da Peça"] == codigo_target]
            
            if not df_filtrado.empty:
                df_filtrado = df_filtrado.copy()
                df_filtrado['_dt_temp'] = pd.to_datetime(df_filtrado["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
                raw_hist = df_filtrado.sort_values('_dt_temp').iloc[-1].to_dict()
                
                last_hist = {}
                for k, v in raw_hist.items():
                    if k == '_dt_temp': continue
                    if pd.isna(v):
                        if k in ["Lote", "Margem Lucro (%)"]: last_hist[k] = 100 if k == "Lote" else 30
                        elif k in ["Usinagem_JSON", "Tratamento_JSON"]: last_hist[k] = "[]"
                        elif any(x in k for x in ["mm", "Kg", "R$", "Preço", "Diâmetro", "Taxa", "Custo"]): last_hist[k] = 0.0
                        else: last_hist[k] = ""
                    else: last_hist[k] = v

                st.session_state["dados_carregados"] = last_hist
                
                st.session_state["sel_empresa_aba1"] = safe_str(last_hist.get("Empresa"))
                st.session_state["txt_comprador"] = safe_str(last_hist.get("Comprador"))
                st.session_state["txt_nome_peca"] = safe_str(last_hist.get("Nome da Peça"))
                st.session_state["num_lote"] = max(1, safe_int(last_hist.get("Lote", 100)))
                st.session_state["num_comprimento"] = max(0.0, safe_float(last_hist.get("Comprimento (mm)")))
                st.session_state["num_margem_corte"] = max(0.0, safe_float(last_hist.get("Margem Corte (mm)", 5.0)))
                st.session_state["sel_tipo_mp"] = safe_str(last_hist.get("Tipo MP", "Por Peso (Barra Maciça/Sextavada)"))
                st.session_state["num_preco_mp"] = max(0.0, safe_float(last_hist.get("Preço MP Unitário")))
                st.session_state["sel_liga"] = safe_str(last_hist.get("Liga", "aço sx"))
                st.session_state["num_diam_barra"] = max(0.0, safe_float(last_hist.get("Diâmetro (mm)", 15.0)))
                st.session_state["num_di_ext"] = max(0.0, safe_float(last_hist.get("Diâmetro Externo (mm)", 20.0)))
                st.session_state["num_di_int"] = max(0.0, safe_float(last_hist.get("Diâmetro Interno (mm)", 10.0)))
                st.session_state["slider_lucro_aba1"] = clip_lucro(safe_int(last_hist.get("Margem Lucro (%)", 30)))
                
                if "Usinagem_JSON" in last_hist and safe_str(last_hist["Usinagem_JSON"]) not in ["", "[]"]:
                    df_usi_carregado = pd.read_json(io.StringIO(last_hist["Usinagem_JSON"]))
                    
                    # PONTO CORRIGIDO: Se a taxa antiga vier como nula (None) de registros antigos, ele puxa o valor padrão de referência atual
                    if "Preço/Hora_Aplicado" in df_usi_carregado.columns:
                        df_usi_carregado["Preço/Hora_Aplicado"] = df_usi_carregado.apply(
                            lambda r: st.session_state.valores_maquinas.get(r["Máquina"], 120.0) if pd.isna(r["Preço/Hora_Aplicado"]) or r["Preço/Hora_Aplicado"] is None else r["Preço/Hora_Aplicado"], axis=1
                        )
                        resumo_taxas = " | ".join([f"{r['Máquina']}: R$ {r['Preço/Hora_Aplicado']}/h" for _, r in df_usi_carregado.drop_duplicates(subset=['Máquina']).iterrows()])
                        st.session_state["taxas_original_msg"] = f"Taxas de hora-maquina aplicadas no último cálculo desta peça: {resumo_taxas}"
                    else:
                        st.session_state["taxas_original_msg"] = "Taxas de hora-máquina: Histórico detalhado indisponível para este registro antigo."
                    
                    st.session_state["df_usinagem_v3"] = df_usi_carregado
                
                if "Tratamento_JSON" in last_hist and safe_str(last_hist["Tratamento_JSON"]) not in ["", "[]"]:
                    st.session_state["df_tratamento_v3"] = pd.read_json(io.StringIO(last_hist["Tratamento_JSON"]))
                    
                st.session_state.editor_version += 1
        except Exception as e:
            st.error(f"Erro ao processar autocomplete: {e}")

valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos

# =============================================================================
# 🧭 3. NAVEGAÇÃO LATERAL
# =============================================================================
st.sidebar.title("🧭 Menu Lenoor")
opcao_menu = st.sidebar.radio(
    "Selecione a tela ativa:",
    ["📊 1. Novo Orçamento", "📜 2. Histórico & Preços Atuais", "⚙️ 3. Configurações de Custos e Impostos"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Lenoor S/A v3.6 - Estabilidade Total")

if opcao_menu != st.session_state.menu_anterior:
    st.session_state["df_recalculado_resultado"] = None  
    st.session_state["taxas_original_msg"] = ""
    st.session_state.menu_anterior = opcao_menu

st.title("Sistema Lenoor de Orçamentos")
st.markdown(f"**Navegação atual:** {opcao_menu}")
st.markdown("---")

# =============================================================================
# 📊 TELA 1: NOVO ORÇAMENTO
# =============================================================================
if opcao_menu == "📊 1. Novo Orçamento":
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    
    with col_cli1:
        opces_empresa = [""] + lista_empresas + ["➕ Novo Cliente..."]
        empresa_sel = st.selectbox("Empresa/Cliente", opces_empresa, key="sel_empresa_aba1")
        if empresa_sel == "➕ Novo Cliente...":
            empresa = st.text_input("Digite o nome do Novo Cliente", placeholder="Ex: TS", key="txt_nova_empresa").strip()
        else: empresa = empresa_sel
            
    with col_cli2:
        comprador = st.text_input("Comprador Responsible", placeholder="Ex: Guilherme", key="txt_comprador").strip()

    st.markdown("---")
    st.subheader("📦 Dados do Produto")
    col_cod_linha1, col_cod_linha2 = st.columns([3, 1])
    
    with col_cod_linha1:
        opcoes_codigo = [""] + lista_codigos + ["➕ Novo Código..."]
        codigo_sel = st.selectbox("Código da Peça (Selecione ou digite para buscar)", opcoes_codigo, key="sel_codigo_peca")
        if codigo_sel == "➕ Novo Código...":
            codigo_peca = st.text_input("Escreva o Código Novo do Produto:", placeholder="Ex: TS-8-030-XXXX", key="txt_novo_codigo").strip()
        else: codigo_peca = codigo_sel

    with col_cod_linha2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True) 
        if codigo_sel and codigo_sel != "➕ Novo Código...":
            st.button("📋 Completar dados com roteiro antigo", type="secondary", use_container_width=True, on_click=carregar_roteiro_antigo_callback)

    if st.session_state["taxas_original_msg"]:
        st.info(st.session_state["taxas_original_msg"])

    col_dados_p1, col_dados_p2, col_dados_p3, col_dados_p4 = st.columns(4)
    with col_dados_p1:
        nome_peca = st.text_input("Nome da Peça", key="txt_nome_peca").strip()
    with col_dados_p2:
        lote = st.number_input("Quantidade do Lote", min_value=1, step=1, key="num_lote")
    with col_dados_p3:
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, step=0.1, key="num_comprimento")
    with col_dados_p4:
        margem_corte = st.number_input("Margem de Corte/Perda (mm)", min_value=0.0, step=0.1, key="num_margem_corte")

    st.markdown("---")
    st.subheader("🧱 Definição da Matéria-Prima")
    opcoes_mp = ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Fornecido pelo Cliente (Mão de Obra Pura)"]
    tipo_mp = st.selectbox("Como a Matéria-Prima será contabilizada?", opcoes_mp, key="sel_tipo_mp")
    
    custo_total_material = 0.0
    total_quilos = 0.0
    preco_unitario_mp = 0.0
    detalhes_material = ""
    material_sel, diametro, di_ext, di_int = "N/A", 0.0, 0.0, 0.0

    if tipo_mp == "Fornecido pelo Cliente (Mão de Obra Pura)":
        total_quilos = st.number_input("Peso total estimado do lote enviado pelo cliente (kg) [Essencial caso haja tratamento]", min_value=0.0, step=0.1, key="num_peso_fornecido")
        detalhes_material = "Fornecido pelo Cliente"
        st.info("ℹ️ Material fornecido pelo parceiro. Custo de MP zerado automaticamente.")
    else:
        col_mat1, col_mat2, col_mat3 = st.columns(3)
        with col_mat1:
            preco_unitario_mp = st.number_input("Preço Atual da MP (R$ por Kg, Metro ou Peça)", min_value=0.0, step=1.0, key="num_preco_mp")

        if "Por Peso" in tipo_mp:
            with col_mat2:
                opcoes_liga = list(DADOS_MATERIAIS.keys())
                material_sel = st.selectbox("Selecione a Liga (Constante)", opcoes_liga, key="sel_liga")
                constante = DADOS_MATERIAIS.get(material_sel, 0.0)
            
            if tipo_mp == "Por Peso (Barra Maciça/Sextavada)":
                with col_mat3:
                    diametro = st.number_input("Diâmetro da Barra (mm)", min_value=0.0, step=0.1, key="num_diam_barra")
                peso_por_metro = ((diametro ** 2) * constante) / 100
            else:
                with col_mat3:
                    di_ext = st.number_input("Diâmetro Externo (mm)", min_value=0.0, step=0.1, key="num_di_ext")
                    di_int = st.number_input("Diâmetro Interno/Furo (mm)", min_value=0.0, step=0.1, key="num_di_int")
                peso_por_metro = max(0.0, ((di_ext ** 2) - (di_int ** 2)) * constante / 100)

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

    # --- PROCESSOS DE USINAGEM ---
    st.subheader("🔨 Roteiro de Processos de Usinagem")
    df_usinagem_input = st.data_editor(
        st.session_state["df_usinagem_v3"],
        num_rows="dynamic",
        column_config={
            "Operação": st.column_config.TextColumn("Operação", required=True),
            "Máquina": st.column_config.SelectboxColumn("Máquina", options=list(valores_maquinas.keys()), required=True),
            "Peças por Hora": st.column_config.NumberColumn("Produção (Pç/h)", min_value=1.0, default=50.0, required=True)
        },
        use_container_width=True,
        key=f"editor_usinagem_aba1_v_{st.session_state.editor_version}"
    )
    
    custo_total_usinagem = 0.0
    if isinstance(df_usinagem_input, pd.DataFrame) and not df_usinagem_input.empty:
        df_usi_clean = df_usinagem_input.fillna({"Peças por Hora": 50.0, "Máquina": "Outro"})
        for idx, row in df_usi_clean.iterrows():
            pcs_h = safe_float(row.get("Peças por Hora"), 50.0)
            if pcs_h <= 0: pcs_h = 50.0
            nome_maq = safe_str(row.get("Máquina"), "Outro")
            custo_total_usinagem += (lote / pcs_h) * valores_maquinas.get(nome_maq, 120.0)

    st.caption(f"💰 Custo de Usinagem: **R$ {custo_total_usinagem:.2f}**")
    st.markdown("---")

    # --- TRATAMENTOS SUPERFICIAIS ---
    st.subheader("✨ Tratamentos Superficiais (Preço por KG)")
    df_trat_input = st.data_editor(
        st.session_state["df_tratamento_v3"],
        num_rows="dynamic",
        column_config={
            "Tratamento": st.column_config.TextColumn("Tratamento", required=True),
            "Preço por Kg (R$)": st.column_config.NumberColumn("Valor por Kg (R$)", min_value=0.0, default=0.0)
        },
        use_container_width=True,
        key=f"editor_tratamentos_aba1_v_{st.session_state.editor_version}"
    )

    soma_preco_kg_tratamento = 0.0
    if isinstance(df_trat_input, pd.DataFrame) and not df_trat_input.empty:
        df_trat_clean = df_trat_input.fillna({"Preço por Kg (R$)": 0.0})
        for idx, row in df_trat_clean.iterrows():
            soma_preco_kg_tratamento += safe_float(row.get("Preço por Kg (R$)"))
            
    custo_total_tratamentos = soma_preco_kg_tratamento * total_quilos
    st.caption(f"✨ Custo total de tratamento: **R$ {custo_total_tratamentos:.2f}**")
    st.markdown("---")

    # --- LUCRO E FECHAMENTO ---
    st.subheader("📈 Margem de Lucro e Fechamento")
    porcentagem_lucro = st.slider("Selecione a Margem de Lucro desejada (%)", min_value=15, max_value=95, step=5, key="slider_lucro_aba1")

    custo_bruto_total = custo_total_material + custo_total_usinagem + custo_total_tratamentos
    
    fator_lucro = (1 - (porcentagem_lucro / 100))
    if fator_lucro <= 0: fator_lucro = 0.05
        
    valor_com_lucro = custo_bruto_total / fator_lucro
    lucro_bruto_real = valor_com_lucro - custo_bruto_total
    total_imposto_pct = safe_float(impostos.get("IR")) + safe_float(impostos.get("FS"))
    valor_impostos = valor_com_lucro * (total_imposto_pct / 100)
    preco_venda_lote = valor_com_lucro + valor_impostos
    preco_unitario_final = preco_venda_lote / lote if lote > 0 else 0.0

    st.markdown("### 📋 Resumo da Proposta Atual")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo Total de Fábrica", f"R$ {custo_bruto_total:.2f}")
    c2.metric("Lucro Bruto Real", f"R$ {lucro_bruto_real:.2f}")
    c3.metric(f"Impostos ({total_imposto_pct}%)", f"R$ {valor_impostos:.2f}")
    c4.metric("Preço UNITÁRIO Final", f"R$ {preco_unitario_final:.2f}")

    if st.button("💾 Gravar no Histórico", type="primary", key="btn_salvar_aba1"):
        if not codigo_peca or codigo_peca == "➕ Novo Código...":
            st.error("Por favor, preencha o código da peça antes de salvar!")
        else:
            if isinstance(df_usinagem_input, pd.DataFrame):
                df_usi_salvamento = df_usinagem_input.copy()
                df_usi_salvamento["Preço/Hora_Aplicado"] = df_usi_salvamento["Máquina"].map(valores_maquinas)
                u_json = df_usi_salvamento.to_json(orient='records')
            else: u_json = "[]"
                
            t_json = df_trat_input.to_json(orient='records') if isinstance(df_trat_input, pd.DataFrame) else "[]"
            
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
                "Usinagem_JSON": u_json,
                "Tratamento_JSON": t_json
            }
            
            df_novo = pd.DataFrame([novo_registro])
            df_hist_atual = ler_historico_seguro()
            df_final = pd.concat([df_hist_atual, df_novo], ignore_index=True) if not df_hist_atual.empty else df_novo
            df_final.to_csv(ARQUIVO_HISTORICO, index=False)
            
            st.session_state["msg_sucesso_persistente"] = f"✅ Sucesso absoluto! O orçamento da peça '{codigo_peca}' foi adicionado e guardado no arquivo histórico!"
            st.toast("💾 Orçamento Gravado com Sucesso!", icon="✅")
            
            st.session_state["dados_carregados"] = {} 
            st.session_state.editor_version += 1
            st.rerun()

    # MUDANÇA ENGENHARIA DE TELAS: O aviso verde agora é renderizado exatamente aqui, logo abaixo do botão de salvar!
    if st.session_state["msg_sucesso_persistente"]:
        st.success(st.session_state["msg_sucesso_persistente"])
        st.session_state["msg_sucesso_persistente"] = ""

# =============================================================================
# 📜 TELA 2: HISTÓRICO & PREÇOS ATUAIS
# =============================================================================
elif opcao_menu == "📜 2. Histórico & Preços Atuais":
    st.subheader("📜 Histórico e Banco de Preços")
    df_completo = ler_historico_seguro()
    
    if df_completo.empty:
        st.info("Nenhum orçamento gerado ainda no sistema.")
    else:
        if "Origem/Alteração" not in df_completo.columns:
            df_completo["Origem/Alteração"] = "Novo Orçamento"
            
        clientes_existentes = sorted(df_completo["Empresa"].dropna().astype(str).unique().tolist())
        cliente_filtro = st.multiselect("🔍 Filtrar por Cliente/Empresa:", options=clientes_existentes, placeholder="Exibindo todos")
        
        opcao_visao = st.radio("Selecione a visualização dos dados:", ["🎯 Preços Atuais (Última Versão por Peça)", "⏳ Histórico de Alterações Completo"], key="rad_visao_aba2")
        
        df_ordenado = df_completo.copy()
        df_ordenado['_datetime_parsed'] = pd.to_datetime(df_ordenado["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
        df_ordenado = df_ordenado.sort_values("_datetime_parsed", ascending=True)
        
        if cliente_filtro:
            df_ordenado = df_ordenado[df_ordenado["Empresa"].isin(cliente_filtro)]

        colunas_comerciais = [
            "Data/Hora", "Origem/Alteração", "Empresa", "Código da Peça", 
            "Nome da Peça", "Lote", "Preço Unitário (R$)", "Preço Total Lote (R$)"
        ]
        
        for col_c in colunas_comerciais:
            if col_c not in df_ordenado.columns: df_ordenado[col_c] = "N/A"
        
        if opcao_visao == "⏳ Histórico de Alterações Completo":
            st.subheader("📋 Registro Cronológico Completo (Limpo)")
            st.dataframe(df_ordenado[colunas_comerciais].iloc[::-1], use_container
