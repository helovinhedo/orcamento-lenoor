import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import io

# =============================================================================
# 🧱 1. CONFIGURAÇÕES INICIAIS E FUNÇÕES UTILITÁRIAS DE SEGURANÇA
# =============================================================================
st.set_page_config(page_title="Sistema Lenoor - Orçamentos", page_icon="⚙️", layout="wide")

ARQUIVO_HISTORICO = "historico_orcamentos_estruturado.csv"
ARQUIVO_CONFIG = "config_lenoor.json"

DEFAULTS_MATERIAIS = {
    "aço sx": {"constante": 0.68, "preco_atual": 0.0, "data_cotacao": ""}, 
    "aço red": {"constante": 0.62, "preco_atual": 0.0, "data_cotacao": ""}, 
    "aço quad": {"constante": 0.72, "preco_atual": 0.0, "data_cotacao": ""},
    "aluminio red": {"constante": 0.212, "preco_atual": 0.0, "data_cotacao": ""}, 
    "aluminio quad": {"constante": 0.212, "preco_atual": 0.0, "data_cotacao": ""}, 
    "aluminio sx": {"constante": 0.212, "preco_atual": 0.0, "data_cotacao": ""},
    "latao red": {"constante": 0.68, "preco_atual": 0.0, "data_cotacao": ""}, 
    "latao quad": {"constante": 0.78, "preco_atual": 0.0, "data_cotacao": ""}, 
    "latao sx": {"constante": 0.72, "preco_atual": 0.0, "data_cotacao": ""}
}

DEFAULTS_MAQUINAS = {
    "CNC": 150.0, "Torno Automático": 120.0, "Freza": 120.0,
    "Furadeira": 70.0, "Torno Revolver": 90.0, "Retífica": 150.0,
    "Serra": 70.0, "Montagem": 90.0, "Outro": 150.0
}
DEFAULTS_IMPOSTOS = {"IR": 6.0, "FS": 4.0}

COLUNAS_PADRAO = [
    "Data/Hora", "Origem/Alteração", "Código da Peça", "Nome da Peça",
    "Empresa", "Comprador", "Lote", "Comprimento (mm)", "Margem Corte (mm)",
    "Tipo MP", "Preço MP Unitário", "Liga", "Diâmetro (mm)", "Diâmetro Externo (mm)",
    "Diâmetro Interno (mm)", "Total Kg Lote", "Custo Material (R$)", "Custo Tratamento (R$)",
    "Margem Lucro (%)", "Preço Total Lote (R$)", "Preço Unitário (R$)", "Usinagem_JSON", "Tratamento_JSON"
]

def safe_float(val, default=0.0):
    try: return default if pd.isna(val) or val is None else float(val)
    except: return default

def safe_int(val, default=0):
    try: return default if pd.isna(val) or val is None else int(float(val))
    except: return default

def safe_str(val, default=""):
    return default if pd.isna(val) or val is None else str(val).strip()

def ler_config_permanente():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r") as f:
                dados = json.load(f)
                if "materiais" not in dados: dados["materiais"] = DEFAULTS_MATERIAIS
                return dados
        except: pass
    return {"valores_maquinas": DEFAULTS_MAQUINAS, "impostos": DEFAULTS_IMPOSTOS, "materiais": DEFAULTS_MATERIAIS}

def salvar_config_permanente(maquinas, impostos, materiais):
    try:
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump({"valores_maquinas": maquinas, "impostos": impostos, "materiais": materiais}, f, indent=4)
    except Exception as e:
        st.error(f"Erro ao salvar config: {e}")

def ler_historico_seguro():
    if not os.path.exists(ARQUIVO_HISTORICO): return pd.DataFrame(columns=COLUNAS_PADRAO)
    try:
        df = pd.read_csv(ARQUIVO_HISTORICO)
        for col in COLUNAS_PADRAO:
            if col not in df.columns: df[col] = None
        return df
    except: return pd.DataFrame(columns=COLUNAS_PADRAO)

# =============================================================================
# 🧠 2. INICIALIZAÇÃO BLINDADA DO COFRE (SESSION STATE)
# =============================================================================
config_carregada = ler_config_permanente()
if "valores_maquinas" not in st.session_state: st.session_state.valores_maquinas = config_carregada["valores_maquinas"]
if "impostos" not in st.session_state: st.session_state.impostos = config_carregada["impostos"]
if "materiais" not in st.session_state: st.session_state.materiais = config_carregada["materiais"]

valores_padrao_widgets = {
    "sel_empresa_aba1": "", "txt_comprador": "", "sel_codigo_peca": "", "txt_nome_peca": "",
    "txt_novo_codigo": "", "txt_nova_empresa": "",
    "num_lote": 100, "num_comprimento": 0.0, "num_margem_corte": 5.0, 
    "sel_tipo_mp": "Por Peso (Barra Maciça/Sextavada)", "num_preco_mp": 0.0, "sel_liga": "aço sx",
    "num_diam_barra": 15.0, "num_di_ext": 20.0, "num_di_int": 10.0, "num_peso_metro": 10.0,
    "num_peso_peca": 10.0, "num_peso_fornecido": 0.0, "slider_lucro_aba1": 30
}
for chave, val in valores_padrao_widgets.items():
    if chave not in st.session_state: st.session_state[chave] = val

if "menu_anterior" not in st.session_state: st.session_state.menu_anterior = ""
if "editor_version" not in st.session_state: st.session_state.editor_version = 0  
if "taxas_original_msg" not in st.session_state: st.session_state["taxas_original_msg"] = ""

# Mensagens de Sucesso Independentes
if "msg_sucesso_aba1" not in st.session_state: st.session_state["msg_sucesso_aba1"] = ""
if "msg_sucesso_aba3" not in st.session_state: st.session_state["msg_sucesso_aba3"] = ""
if "msg_sucesso_aba4" not in st.session_state: st.session_state["msg_sucesso_aba4"] = ""

if "df_usinagem_v3" not in st.session_state:
    st.session_state["df_usinagem_v3"] = pd.DataFrame([{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50.0}])
if "df_tratamento_v3" not in st.session_state:
    st.session_state["df_tratamento_v3"] = pd.DataFrame([{"Tratamento": "Nenhum", "Preço por Kg (R$)": 0.0}])

def limpar_formulario_orcamento():
    for k, v in valores_padrao_widgets.items(): st.session_state[k] = v
    st.session_state["df_usinagem_v3"] = pd.DataFrame([{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50.0}])
    st.session_state["df_tratamento_v3"] = pd.DataFrame([{"Tratamento": "Nenhum", "Preço por Kg (R$)": 0.0}])
    st.session_state["taxas_original_msg"] = ""
    st.session_state.editor_version += 1

# Listas do histórico globais (usadas primariamente na Tela 1)
df_init = ler_historico_seguro()
lista_empresas = sorted(df_init["Empresa"].dropna().astype(str).unique().tolist()) if not df_init.empty else []
empresa_atual = st.session_state.get("sel_empresa_aba1", "")
if empresa_atual and empresa_atual != "➕ Novo Cliente...":
    lista_codigos = sorted(df_init[df_init["Empresa"] == empresa_atual]["Código da Peça"].dropna().astype(str).unique().tolist())
else:
    lista_codigos = sorted(df_init["Código da Peça"].dropna().astype(str).unique().tolist()) if not df_init.empty else []

def carregar_roteiro_antigo_callback():
    codigo_target = st.session_state.get("sel_codigo_peca", "")
    if codigo_target and codigo_target != "➕ Novo Código...":
        try:
            df_hist = ler_historico_seguro()
            df_filtrado = df_hist[df_hist["Código da Peça"] == codigo_target].copy()
            if not df_filtrado.empty:
                df_filtrado['_dt_temp'] = pd.to_datetime(df_filtrado["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
                last_hist = df_filtrado.sort_values('_dt_temp').iloc[-1].fillna("").to_dict()
                
                st.session_state["sel_empresa_aba1"] = safe_str(last_hist.get("Empresa"))
                st.session_state["txt_comprador"] = safe_str(last_hist.get("Comprador"))
                st.session_state["txt_nome_peca"] = safe_str(last_hist.get("Nome da Peça"))
                st.session_state["num_lote"] = max(1, safe_int(last_hist.get("Lote", 100)))
                st.session_state["num_comprimento"] = max(0.0, safe_float(last_hist.get("Comprimento (mm)")))
                st.session_state["num_margem_corte"] = max(0.0, safe_float(last_hist.get("Margem Corte (mm)", 5.0)))
                st.session_state["sel_tipo_mp"] = safe_str(last_hist.get("Tipo MP", "Por Peso (Barra Maciça/Sextavada)"))
                
                liga_salva = safe_str(last_hist.get("Liga", "aço sx"))
                st.session_state["sel_liga"] = liga_salva
                preco_hist = safe_float(last_hist.get("Preço MP Unitário"))
                st.session_state["num_preco_mp"] = st.session_state.materiais.get(liga_salva, {}).get("preco_atual", preco_hist) if "Por Peso" in st.session_state["sel_tipo_mp"] else preco_hist

                st.session_state["num_diam_barra"] = max(0.0, safe_float(last_hist.get("Diâmetro (mm)", 15.0)))
                st.session_state["num_di_ext"] = max(0.0, safe_float(last_hist.get("Diâmetro Externo (mm)", 20.0)))
                st.session_state["num_di_int"] = max(0.0, safe_float(last_hist.get("Diâmetro Interno (mm)", 10.0)))
                st.session_state["slider_lucro_aba1"] = max(15, min(safe_int(last_hist.get("Margem Lucro (%)", 30)), 95))
                
                if "Usinagem_JSON" in last_hist and safe_str(last_hist["Usinagem_JSON"]) not in ["", "[]"]:
                    df_usi = pd.read_json(io.StringIO(str(last_hist["Usinagem_JSON"])), orient='records')
                    for col in ["Operação", "Máquina", "Peças por Hora"]:
                        if col not in df_usi.columns: df_usi[col] = "Outro" if col == "Máquina" else (50.0 if col == "Peças por Hora" else "")
                    
                    if "Preço/Hora_Aplicado" in df_usi.columns:
                        resumo = " | ".join([f"{r['Máquina']}: R$ {r['Preço/Hora_Aplicado']}/h" for _, r in df_usi.drop_duplicates(subset=['Máquina']).iterrows()])
                        st.session_state["taxas_original_msg"] = f"Últimas taxas de máquina: {resumo}"
                    else: st.session_state["taxas_original_msg"] = ""
                    st.session_state["df_usinagem_v3"] = df_usi[["Operação", "Máquina", "Peças por Hora"]].copy()
                
                if "Tratamento_JSON" in last_hist and safe_str(last_hist["Tratamento_JSON"]) not in ["", "[]"]:
                    df_trat = pd.read_json(io.StringIO(str(last_hist["Tratamento_JSON"])))
                    st.session_state["df_tratamento_v3"] = df_trat[["Tratamento", "Preço por Kg (R$)"]].copy()
                    
                st.session_state.editor_version += 1
        except Exception as e: st.toast(f"Erro no autocomplete: {e}", icon="⚠️")

valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos
materiais = st.session_state.materiais

# =============================================================================
# 🧭 3. NAVEGAÇÃO LATERAL E TÍTULO
# =============================================================================
st.sidebar.title("🧭 Menu Lenoor")
opcoes = ["📊 1. Novo Orçamento", "📜 2. Histórico de Peças", "🧱 3. Matéria-Prima", "⚙️ 4. Custos Fixos & BD", "🛒 5. Cotação Final"]
opcao_menu = st.sidebar.radio("Navegação:", opcoes)

# A Cereja do Bolo: Versão no Menu Lateral
st.sidebar.markdown("---")
st.sidebar.caption("Lenoor S/A v4.0 - Arquitetura Final")

# Limpa mensagens ao mudar de tela
if opcao_menu != st.session_state.menu_anterior:
    st.session_state["taxas_original_msg"] = ""
    st.session_state["msg_sucesso_aba1"] = ""
    st.session_state["msg_sucesso_aba3"] = ""
    st.session_state["msg_sucesso_aba4"] = ""
    st.session_state.menu_anterior = opcao_menu

titulo_limpo = opcao_menu.split('. ')[1] if '. ' in opcao_menu else opcao_menu
st.title(titulo_limpo)
st.markdown("---")

# =============================================================================
# 📊 TELA 1: NOVO ORÇAMENTO
# =============================================================================
if opcao_menu == "📊 1. Novo Orçamento":
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    with col_cli1:
        opces_empresa = [""] + lista_empresas + ["➕ Novo Cliente..."]
        try: idx_emp = opces_empresa.index(st.session_state["sel_empresa_aba1"])
        except: idx_emp = 0
        empresa_sel = st.selectbox("Empresa/Cliente", opces_empresa, index=idx_emp)
        st.session_state["sel_empresa_aba1"] = empresa_sel
        
        # Correção do Bug Fantasma
        if empresa_sel == "➕ Novo Cliente...":
            nova_emp = st.text_input("Novo Cliente", value=st.session_state["txt_nova_empresa"])
            st.session_state["txt_nova_empresa"] = nova_emp
            empresa = nova_emp.strip()
        else:
            empresa = empresa_sel
            
    with col_cli2:
        comprador = st.text_input("Comprador", value=st.session_state["txt_comprador"])
        st.session_state["txt_comprador"] = comprador

    st.markdown("---")
    st.subheader("📦 Dados do Produto")
    col_cod_linha1, col_cod_linha2 = st.columns([3, 1])
    with col_cod_linha1:
        opcoes_codigo = [""] + lista_codigos + ["➕ Novo Código..."]
        try: idx_cod = opcoes_codigo.index(st.session_state["sel_codigo_peca"])
        except: idx_cod = 0
        codigo_sel = st.selectbox("Código da Peça", opcoes_codigo, index=idx_cod)
        st.session_state["sel_codigo_peca"] = codigo_sel
        
        if codigo_sel == "➕ Novo Código...":
            novo_cod = st.text_input("Novo Código:", value=st.session_state["txt_novo_codigo"])
            st.session_state["txt_novo_codigo"] = novo_cod
            codigo_peca = novo_cod.strip()
        else:
            codigo_peca = codigo_sel

    with col_cod_linha2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True) 
        if codigo_sel and codigo_sel != "➕ Novo Código...":
            st.button("Completar Dados", type="primary", use_container_width=True, on_click=carregar_roteiro_antigo_callback)

    if st.session_state["taxas_original_msg"]: st.info(st.session_state["taxas_original_msg"])

    col_dados_p1, col_dados_p2, col_dados_p3, col_dados_p4 = st.columns(4)
    with col_dados_p1:
        nome_peca = st.text_input("Nome da Peça", value=st.session_state["txt_nome_peca"])
        st.session_state["txt_nome_peca"] = nome_peca
    with col_dados_p2:
        lote = st.number_input("Lote", min_value=1, step=1, value=int(st.session_state["num_lote"]))
        st.session_state["num_lote"] = lote
    with col_dados_p3:
        comprimento = st.number_input("Comprimento (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_comprimento"]))
        st.session_state["num_comprimento"] = comprimento
    with col_dados_p4:
        margem_corte = st.number_input("Corte/Perda (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_margem_corte"]))
        st.session_state["num_margem_corte"] = margem_corte

    st.markdown("---")
    st.subheader("🧱 Matéria-Prima")
    opcoes_mp = ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Mão de Obra Pura (Fornecido)"]
    try: idx_mp = opcoes_mp.index(st.session_state["sel_tipo_mp"])
    except: idx_mp = 0
    tipo_mp = st.selectbox("Contabilização", opcoes_mp, index=idx_mp)
    st.session_state["sel_tipo_mp"] = tipo_mp
    
    custo_total_material, total_quilos, preco_unitario_mp, material_sel = 0.0, 0.0, 0.0, "N/A"
    diametro, di_ext, di_int = 0.0, 0.0, 0.0

    if tipo_mp == "Mão de Obra Pura (Fornecido)":
        total_quilos = st.number_input("Peso total lote (kg) [Tratamento]", min_value=0.0, step=0.1, value=float(st.session_state["num_peso_fornecido"]))
        st.session_state["num_peso_fornecido"] = total_quilos
    else:
        col_mat1, col_mat2, col_mat3 = st.columns(3)
        with col_mat1:
            preco_unitario_mp = st.number_input("Preço Atual MP (R$)", min_value=0.0, step=1.0, value=float(st.session_state["num_preco_mp"]))
            st.session_state["num_preco_mp"] = preco_unitario_mp

        if "Por Peso" in tipo_mp:
            with col_mat2:
                opcoes_liga = list(materiais.keys())
                try: idx_liga = opcoes_liga.index(st.session_state["sel_liga"])
                except: idx_liga = 0
                material_sel = st.selectbox("Liga", opcoes_liga, index=idx_liga)
                st.session_state["sel_liga"] = material_sel
                constante = materiais.get(material_sel, {}).get("constante", 0.0)
            
            if "Maciça" in tipo_mp:
                with col_mat3:
                    diametro = st.number_input("Diâmetro (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_diam_barra"]))
                    st.session_state["num_diam_barra"] = diametro
                peso_por_metro = ((diametro ** 2) * constante) / 100
            else:
                with col_mat3:
                    di_ext = st.number_input("Diâm. Ext. (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_di_ext"]))
                    di_int = st.number_input("Diâm. Int. (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_di_int"]))
                    st.session_state["num_di_ext"] = di_ext
                    st.session_state["num_di_int"] = di_int
                peso_por_metro = max(0.0, ((di_ext ** 2) - (di_int ** 2)) * constante / 100)

            total_metros = ((comprimento + margem_corte) * lote) / 1000
            total_quilos = total_metros * peso_por_metro
            custo_total_material = total_quilos * preco_unitario_mp

        elif tipo_mp == "Por Metro Linear":
            total_metros = ((comprimento + margem_corte) * lote) / 1000
            custo_total_material = total_metros * preco_unitario_mp
            with col_mat2:
                total_quilos = st.number_input("Peso total lote (kg)", min_value=0.0, step=0.1, value=float(st.session_state["num_peso_metro"]))
                st.session_state["num_peso_metro"] = total_quilos

        elif tipo_mp == "Por Peça Pronta":
            custo_total_material = lote * preco_unitario_mp
            with col_mat2:
                total_quilos = st.number_input("Peso total lote (kg)", min_value=0.0, step=0.1, value=float(st.session_state["num_peso_peca"]))
                st.session_state["num_peso_peca"] = total_quilos

    st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}", help=f"{total_quilos:.2f} kg")
    st.markdown("---")

    # --- PROCESSOS DE USINAGEM ---
    st.subheader("🔨 Usinagem")
    df_usinagem_input = st.data_editor(
        st.session_state["df_usinagem_v3"],
        num_rows="dynamic",
        column_config={
            "Operação": st.column_config.TextColumn("Operação", required=True),
            "Máquina": st.column_config.SelectboxColumn("Máquina", options=list(valores_maquinas.keys()), required=True),
            "Peças por Hora": st.column_config.NumberColumn("Produção (Pç/h)", min_value=0.1, step=1.0, default=50.0)
        },
        use_container_width=True,
        key=f"editor_usi_{st.session_state.editor_version}"
    )
    
    custo_total_usinagem = 0.0
    if not df_usinagem_input.empty:
        df_usi_clean = df_usinagem_input.fillna({"Peças por Hora": 50.0, "Máquina": "Outro"})
        for _, row in df_usi_clean.iterrows():
            pcs_h = max(0.1, safe_float(row.get("Peças por Hora"), 50.0))
            custo_total_usinagem += (lote / pcs_h) * valores_maquinas.get(safe_str(row.get("Máquina"), "Outro"), 120.0)

    st.caption(f"Custo de Usinagem: **R$ {custo_total_usinagem:.2f}**")
    st.markdown("---")

    # --- TRATAMENTOS ---
    st.subheader("✨ Tratamentos (Preço/KG)")
    df_trat_input = st.data_editor(
        st.session_state["df_tratamento_v3"],
        num_rows="dynamic",
        column_config={
            "Tratamento": st.column_config.TextColumn("Tratamento", required=True),
            "Preço por Kg (R$)": st.column_config.NumberColumn("Valor por Kg", min_value=0.0, step=0.01, format="R$ %.2f", default=0.0)
        },
        use_container_width=True,
        key=f"editor_trat_{st.session_state.editor_version}"
    )

    soma_preco_kg_tratamento = 0.0
    if not df_trat_input.empty:
        df_trat_clean = df_trat_input.fillna({"Preço por Kg (R$)": 0.0})
        for _, row in df_trat_clean.iterrows():
            soma_preco_kg_tratamento += safe_float(row.get("Preço por Kg (R$)"))
            
    custo_total_tratamentos = soma_preco_kg_tratamento * total_quilos
    st.caption(f"Custo Tratamento: **R$ {custo_total_tratamentos:.2f}**")
    st.markdown("---")

    # --- FECHAMENTO E SALVAMENTO ---
    porcentagem_lucro = st.slider("Margem de Lucro (%)", 15, 95, int(st.session_state["slider_lucro_aba1"]), 5)
    st.session_state["slider_lucro_aba1"] = porcentagem_lucro

    custo_bruto = custo_total_material + custo_total_usinagem + custo_total_tratamentos
    fator_lucro = max(0.05, (1 - (porcentagem_lucro / 100)))
    valor_venda_bruto = custo_bruto / fator_lucro
    total_imp_pct = safe_float(impostos.get("IR")) + safe_float(impostos.get("FS"))
    valor_impostos = valor_venda_bruto * (total_imp_pct / 100)
    preco_lote = valor_venda_bruto + valor_impostos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo de Fábrica", f"R$ {custo_bruto:.2f}")
    c2.metric("Lucro Bruto", f"R$ {valor_venda_bruto - custo_bruto:.2f}")
    c3.metric(f"Impostos ({total_imp_pct}%)", f"R$ {valor_impostos:.2f}")
    c4.metric("Preço UNITÁRIO", f"R$ {preco_lote / lote if lote > 0 else 0.0:.2f}")

    if st.button("💾 Gravar no Histórico", type="primary"):
        if not codigo_peca or codigo_peca == "➕ Novo Código...":
            st.error("Preencha o código da peça!")
        else:
            df_usi_salvar = df_usinagem_input.copy()
            if not df_usi_salvar.empty: df_usi_salvar["Preço/Hora_Aplicado"] = df_usi_salvar["Máquina"].map(valores_maquinas)
            
            novo_registro = {
                "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"), "Origem/Alteração": "Novo Orçamento",
                "Código da Peça": codigo_peca, "Nome da Peça": nome_peca, "Empresa": empresa, "Comprador": comprador,
                "Lote": lote, "Comprimento (mm)": comprimento, "Margem Corte (mm)": margem_corte, "Tipo MP": tipo_mp,
                "Preço MP Unitário": preco_unitario_mp, "Liga": material_sel, "Diâmetro (mm)": diametro,
                "Diâmetro Externo (mm)": di_ext, "Diâmetro Interno (mm)": di_int, "Total Kg Lote": round(total_quilos, 3),
                "Custo Material (R$)": round(custo_total_material, 2), "Custo Tratamento (R$)": round(custo_total_tratamentos, 2),
                "Margem Lucro (%)": porcentagem_lucro, "Preço Total Lote (R$)": round(preco_lote, 2),
                "Preço Unitário (R$)": round(preco_lote / lote if lote > 0 else 0.0, 2),
                "Usinagem_JSON": df_usi_salvar.to_json(orient='records'),
                "Tratamento_JSON": df_trat_input.to_json(orient='records')
            }
            df_final = pd.concat([df_init, pd.DataFrame([novo_registro])], ignore_index=True) if not df_init.empty else pd.DataFrame([novo_registro])
            df_final.to_csv(ARQUIVO_HISTORICO, index=False)
            
            limpar_formulario_orcamento()
            st.session_state["msg_sucesso_aba1"] = f"✅ Orçamento da peça '{codigo_peca}' gravado com sucesso!"
            st.rerun()

    if st.session_state.get("msg_sucesso_aba1"):
        st.success(st.session_state["msg_sucesso_aba1"])
        st.session_state["msg_sucesso_aba1"] = ""
# =============================================================================
# 📚 MÓDULO DE AJUDA E DOCUMENTAÇÃO (RODAPÉ PERSISTENTE)
# =============================================================================
    st.markdown("---")
    with st.expander("❓ Entenda os Cálculos do Sistema (Fórmulas e Regras)"):
        st.markdown("Este sistema foi desenhado com engenharia de custos precisa. Abaixo estão as fórmulas matemáticas abertas para fins de auditoria e governança:")
        
        st.markdown("#### 🧱 1. Cálculo de Tubos e Buchas")
        st.markdown("O sistema calcula o peso de 1 metro linear do tubo como se fosse uma barra maciça e subtrai o 'miolo' vazio, utilizando a constante de densidade da liga selecionada.")
        st.latex(r"Peso/Metro = \frac{(D_{ext}^2 - D_{int}^2) \times Constante\_da\_Liga}{100}")
        
        st.markdown("#### 🔨 2. Custo de Usinagem")
        st.markdown("Baseado na produção por hora inserida no roteiro. O sistema descobre quantas horas a máquina vai trabalhar no lote inteiro e multiplica pela tarifa R$/hora.")
        st.latex(r"Custo\_Usinagem = \left( \frac{Tamanho\_do\_Lote}{Pe\text{\c{c}}as\_por\_Hora} \right) \times Taxa\_M\acute{a}quina\_(R\$/h)")
        
        st.markdown("#### 💰 3. Formação do Preço de Venda (Markup Divisor)")
        st.markdown("O sistema calcula o valor de venda de forma *Bottom-Up* (de baixo para cima), garantindo que a **Margem de Lucro Bruta (%)** informada seja um ganho real sobre o faturamento de fábrica, e não apenas um acréscimo simples.")
        st.latex(r"Faturamento\_Bruto = \frac{Custo\_de\_F\acute{a}brica}{1 - \left( \frac{Margem\%}{100} \right)}")
        
        st.markdown("#### 🧾 4. Impostos (Guias)")
        st.markdown("Os impostos são calculados estritamente sobre o Faturamento Bruto projetado (antes do acréscimo do próprio imposto no preço final).")

# =============================================================================
# 📜 TELA 2: HISTÓRICO COM FILTRO EM CASCATA
# =============================================================================
elif opcao_menu == "📜 2. Histórico de Peças":
    if df_init.empty: st.info("Nenhum orçamento gerado.")
    else:
        c_filt1, c_filt2 = st.columns(2)
        with c_filt1: cliente_filtro = st.multiselect("🔍 Cliente:", options=lista_empresas)
        
        todos_os_codigos = sorted(df_init["Código da Peça"].dropna().astype(str).unique())
        codigos_disp = sorted(df_init[df_init["Empresa"].isin(cliente_filtro)]["Código da Peça"].dropna().astype(str).unique()) if cliente_filtro else todos_os_codigos
        with c_filt2: codigo_filtro = st.multiselect("🔍 Código:", options=codigos_disp)
        
        opcao_visao = st.radio("Visualização:", ["🎯 Preços Atuais (Última Versão)", "⏳ Histórico Completo"])
        
        df_ord = df_init.copy()
        df_ord['_dt'] = pd.to_datetime(df_ord["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
        df_ord = df_ord.sort_values("_dt", ascending=True)
        if cliente_filtro: df_ord = df_ord[df_ord["Empresa"].isin(cliente_filtro)]
        if codigo_filtro: df_ord = df_ord[df_ord["Código da Peça"].isin(codigo_filtro)]

        cols = ["Data/Hora", "Origem/Alteração", "Empresa", "Código da Peça", "Nome da Peça", "Lote", "Preço Unitário (R$)", "Preço Total Lote (R$)"]
        for c in cols: 
            if c not in df_ord.columns: df_ord[c] = "N/A"
        
        if "Completo" in opcao_visao: st.dataframe(df_ord[cols].iloc[::-1], use_container_width=True)
        else:
            df_ult = df_ord.groupby("Código da Peça").last().reset_index().sort_values("Empresa")
            st.dataframe(df_ult[["Empresa", "Código da Peça", "Nome da Peça", "Lote", "Preço Unitário (R$)", "Preço Total Lote (R$)"]], use_container_width=True)

# =============================================================================
# 🧱 TELA 3: MATÉRIA-PRIMA E RECÁLCULO INTELIGENTE
# =============================================================================
elif opcao_menu == "🧱 3. Matéria-Prima":
    st.write("Atualize os preços. A data de cotação atualiza automaticamente.")
    
    df_mat = pd.DataFrame.from_dict(materiais, orient="index").reset_index()
    df_mat.rename(columns={"index": "Liga", "preco_atual": "Preço Atual (R$/Kg)", "data_cotacao": "Data da Cotação"}, inplace=True)
    
    df_mat_edit = st.data_editor(
        df_mat,
        column_config={
            "Liga": st.column_config.TextColumn(disabled=True),
            "constante": st.column_config.NumberColumn("Constante Peso", disabled=True),
            "Preço Atual (R$/Kg)": st.column_config.NumberColumn(min_value=0.0, step=0.1, format="R$ %.2f"),
            "Data da Cotação": st.column_config.TextColumn(disabled=True)
        },
        use_container_width=True, hide_index=True
    )

    if st.button("💾 Salvar Novos Preços de Materiais", type="primary"):
        novos_materiais = {}
        mudancas = False
        hoje = datetime.now().strftime("%d/%m/%Y")
        
        # Arquivo separado para o histórico de auditoria de compras de MP
        ARQUIVO_AUDITORIA_MP = "historico_compras_mp.csv"
        registros_auditoria = []

        for _, row in df_mat_edit.iterrows():
            liga = row["Liga"]
            preco_novo = float(row["Preço Atual (R$/Kg)"])
            preco_antigo = materiais[liga]["preco_atual"]
            
            if preco_novo != preco_antigo: 
                mudancas = True
                # Se mudou, cria o registro para o arquivo apartado
                registros_auditoria.append({
                    "Data Alteração": hoje,
                    "Liga/Material": liga,
                    "Preço Antigo (R$)": preco_antigo,
                    "Preço Novo (R$)": preco_novo
                })
                
            novos_materiais[liga] = {
                "constante": float(row["constante"]), 
                "preco_atual": preco_novo, 
                "data_cotacao": hoje if preco_novo != preco_antigo else materiais[liga]["data_cotacao"]
            }
            
        if mudancas:
            # 1. Salva a configuração atual de trabalho
            st.session_state.materiais = novos_materiais
            salvar_config_permanente(valores_maquinas, impostos, novos_materiais)
            
            # 2. Salva o registro no arquivo apartado de histórico de compras
            if registros_auditoria:
                df_auditoria_novo = pd.DataFrame(registros_auditoria)
                if os.path.exists(ARQUIVO_AUDITORIA_MP):
                    try:
                        df_auditoria_antigo = pd.read_csv(ARQUIVO_AUDITORIA_MP)
                        df_auditoria_final = pd.concat([df_auditoria_antigo, df_auditoria_novo], ignore_index=True)
                    except:
                        df_auditoria_final = df_auditoria_novo
                else:
                    df_auditoria_final = df_auditoria_novo
                df_auditoria_final.to_csv(ARQUIVO_AUDITORIA_MP, index=False)
                
            st.toast("✅ Preços atualizados e registrados no histórico de compras!")
            st.rerun()
            # --- DASHBOARD VISUAL DO HISTÓRICO DE COMPRAS ---
    ARQUIVO_AUDITORIA_MP = "historico_compras_mp.csv"
    with st.expander("📈 Ver Histórico de Evolução de Preços (MP)"):
        if not os.path.exists(ARQUIVO_AUDITORIA_MP):
            st.info("Nenhum histórico de alteração de preços registrado ainda.")
        else:
            try:
                df_aud = pd.read_csv(ARQUIVO_AUDITORIA_MP)
                
                # Filtro dinâmico para o gráfico não ficar poluído
                materiais_historico = sorted(df_aud["Liga/Material"].unique().tolist())
                mat_grafico = st.selectbox("Escolha o material para ver o gráfico de evolução:", materiais_historico, key="recalc_graf_mp")
                
                df_filtrado_graf = df_aud[df_aud["Liga/Material"] == mat_grafico].copy()
                
                if not df_filtrado_graf.empty:
                    # Monta o gráfico de linha estético
                    st.markdown(f"#### Tendência de Preço - {mat_grafico}")
                    df_graf_exibir = df_filtrado_graf.set_index("Data Alteração")[["Preço Novo (R$)"]]
                    st.line_chart(df_graf_exibir, use_container_width=True)
                    
                    # Tabela detalhada reversa (mais recente primeiro)
                    st.markdown("#### Lista de Alterações")
                    st.dataframe(df_filtrado_graf.iloc[::-1], hide_index=True, use_container_width=True)
                    
                    # Botão para baixar a planilha limpa em CSV do histórico de compras se precisar
                    csv_aud = df_filtrado_graf.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Histórico deste Material", data=csv_aud, file_name=f"historico_precos_{mat_grafico}.csv", mime="text/csv")
            except:
                st.error("Erro ao carregar o arquivo de histórico de compras de MP.")
            
    st.markdown("---")
    st.subheader("🔄 Recalcular por Material")
    if not df_init.empty:
        liga_recalc = st.selectbox("Selecione a Liga que sofreu alteração:", [""] + list(materiais.keys()))
        if liga_recalc:
            df_ultimos = df_init.sort_values(by="Data/Hora").groupby("Código da Peça").last().reset_index()
            df_afetados = df_ultimos[(df_ultimos["Liga"] == liga_recalc) & (df_ultimos["Tipo MP"].str.contains("Peso"))].copy()
            
            if df_afetados.empty: st.info("Nenhuma peça mapeada por peso usa esta liga.")
            else:
                st.warning("⚠️ O recálculo utilizará os valores SALVOS no sistema. Se você alterou o preço acima, clique em 'Salvar' antes de prosseguir.")
                st.write(f"Preço salvo para **{liga_recalc}**: R$ {materiais[liga_recalc]['preco_atual']:.2f}")
                
                df_afetados.insert(0, "Recalcular", True)
                
                # Desabilita edições acidentais (blindagem da tabela)
                df_afetados_edit = st.data_editor(
                    df_afetados[["Recalcular", "Empresa", "Código da Peça", "Nome da Peça", "Lote", "Total Kg Lote"]],
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Recalcular": st.column_config.CheckboxColumn("Recalcular?"),
                        "Empresa": st.column_config.TextColumn(disabled=True),
                        "Código da Peça": st.column_config.TextColumn(disabled=True),
                        "Nome da Peça": st.column_config.TextColumn(disabled=True),
                        "Lote": st.column_config.NumberColumn(disabled=True),
                        "Total Kg Lote": st.column_config.NumberColumn(disabled=True)
                    }
                )
                
                if st.button("🚀 Executar Recálculo de MP"):
                    codigos_selecionados = df_afetados_edit[df_afetados_edit["Recalcular"]]["Código da Peça"].tolist()
                    novas_linhas = []
                    novo_preco_mp = materiais[liga_recalc]['preco_atual']
                    
                    for _, row in df_afetados[df_afetados["Código da Peça"].isin(codigos_selecionados)].iterrows():
                        row_dict = row.to_dict()
                        
                        row_dict["Preço MP Unitário"] = novo_preco_mp
                        row_dict["Custo Material (R$)"] = round(safe_float(row_dict.get("Total Kg Lote", 0.0)) * novo_preco_mp, 2)
                        
                        roteiro_raw = row_dict.get("Usinagem_JSON", "[]")
                        roteiro = json.loads(roteiro_raw) if isinstance(roteiro_raw, str) else []
                        custo_usinagem_antigo = 0.0
                        lote_val = max(1, safe_int(row_dict.get("Lote", 100)))
                        
                        if isinstance(roteiro, list):
                            for op in roteiro:
                                pcs_h = max(0.1, safe_float(op.get("Peças por Hora"), 50.0))
                                maq_nome = safe_str(op.get("Máquina"), "Outro")
                                taxa_hora = safe_float(op.get("Preço/Hora_Aplicado", valores_maquinas.get(maq_nome, 120.0)))
                                custo_usinagem_antigo += (lote_val / pcs_h) * taxa_hora
                        
                        custo_bruto = row_dict["Custo Material (R$)"] + custo_usinagem_antigo + safe_float(row_dict.get("Custo Tratamento (R$)"))
                        fator_l = max(0.05, (1 - (safe_float(row_dict.get("Margem Lucro (%)", 30)) / 100)))
                        valor_venda = custo_bruto / fator_l
                        imp_pct = safe_float(impostos.get("IR")) + safe_float(impostos.get("FS"))
                        preco_final = valor_venda + (valor_venda * (imp_pct / 100))
                        
                        row_dict["Preço Total Lote (R$)"] = round(preco_final, 2)
                        row_dict["Preço Unitário (R$)"] = round(preco_final / lote_val, 2)
                        row_dict["Origem/Alteração"] = "Recálculo de MP"
                        row_dict["Data/Hora"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        
                        if "Recalcular" in row_dict: del row_dict["Recalcular"]
                        if "_dt_temp" in row_dict: del row_dict["_dt_temp"]
                        
                        novas_linhas.append(row_dict)
                        
                    if novas_linhas:
                        df_final_salvar = pd.concat([df_init, pd.DataFrame(novas_linhas)], ignore_index=True)
                        df_final_salvar.to_csv(ARQUIVO_HISTORICO, index=False)
                        st.session_state["msg_sucesso_aba3"] = f"✅ {len(novas_linhas)} peças recalculadas com sucesso pela troca de MP!"
                        st.rerun()

    if st.session_state.get("msg_sucesso_aba3"):
        st.success(st.session_state["msg_sucesso_aba3"])
        st.session_state["msg_sucesso_aba3"] = ""

# =============================================================================
# ⚙️ TELA 4: CUSTOS FIXOS E RECÁLCULO INTELIGENTE
# =============================================================================
elif opcao_menu == "⚙️ 4. Custos Fixos & BD":
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 💰 Hora-Máquina (R$/h)")
        df_maq = pd.DataFrame(list(valores_maquinas.items()), columns=["Máquina", "Taxa (R$/h)"])
        df_maq_edit = st.data_editor(
            df_maq, hide_index=True, use_container_width=True,
            column_config={"Máquina": st.column_config.TextColumn(disabled=True), "Taxa (R$/h)": st.column_config.NumberColumn(min_value=0.0, step=5.0, format="R$ %.2f")}
        )
        
    with c2:
        st.markdown("#### 📝 Impostos (%)")
        df_imp = pd.DataFrame(list(impostos.items()), columns=["Imposto", "Taxa (%)"])
        df_imp_edit = st.data_editor(
            df_imp, hide_index=True, use_container_width=True,
            column_config={"Imposto": st.column_config.TextColumn(disabled=True), "Taxa (%)": st.column_config.NumberColumn(min_value=0.0, step=0.5)}
        )

    if st.button("💾 Salvar Taxas e Impostos", type="primary"):
        novas_maq = dict(zip(df_maq_edit["Máquina"], df_maq_edit["Taxa (R$/h)"]))
        novos_imp = dict(zip(df_imp_edit["Imposto"], df_imp_edit["Taxa (%)"]))
        st.session_state.valores_maquinas = novas_maq
        st.session_state.impostos = novos_imp
        salvar_config_permanente(novas_maq, novos_imp, materiais)
        st.toast("✅ Taxas atualizadas!")
        st.rerun()

    st.markdown("---")
    st.subheader("🔄 Recálculo de Tarifas (Hora-Máquina e Impostos)")
    if not df_init.empty:
        # Filtro Inteligente Único
        opcoes_motivo = [""] + ["Recálculo Geral (Use para Impostos ou Múltiplas Máquinas)"] + [f"Máquina: {m}" for m in valores_maquinas.keys()]
        motivo_recalc = st.selectbox("Qual tarifa motivou este recálculo?", opcoes_motivo)
        
        if motivo_recalc:
            clientes_selecionados = st.multiselect("Filtrar clientes (vazio = TODOS):", options=lista_empresas)
            
            df_ultimos = df_init.copy()
            df_ultimos['_dt_temp'] = pd.to_datetime(df_ultimos["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
            df_ultimos = df_ultimos.sort_values("_dt_temp").groupby("Código da Peça").last().reset_index()
            
            if clientes_selecionados: 
                df_ultimos = df_ultimos[df_ultimos["Empresa"].isin(clientes_selecionados)]
                
            # Lógica de Filtragem Cirúrgica pelo JSON
            if "Impostos" not in motivo_recalc:
                maq_alvo = motivo_recalc.replace("Máquina: ", "")
                df_ultimos = df_ultimos[df_ultimos["Usinagem_JSON"].apply(lambda x: maq_alvo in str(x))]
            
            if df_ultimos.empty:
                st.info("Nenhuma peça encontrada com estes critérios.")
            else:
                st.warning("⚠️ O recálculo utilizará as taxas SALVAS. Se alterou valores acima, clique em 'Salvar' antes.")
                df_ultimos.insert(0, "Recalcular", True)
                
                # Desabilita edições acidentais
                df_recalc_edit = st.data_editor(
                    df_ultimos[["Recalcular", "Empresa", "Código da Peça", "Nome da Peça", "Lote"]],
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Recalcular": st.column_config.CheckboxColumn("Recalcular?"),
                        "Empresa": st.column_config.TextColumn(disabled=True),
                        "Código da Peça": st.column_config.TextColumn(disabled=True),
                        "Nome da Peça": st.column_config.TextColumn(disabled=True),
                        "Lote": st.column_config.NumberColumn(disabled=True)
                    }
                )
                
                if st.button("🚀 Executar Recálculo de Tarifas"):
                    codigos_selecionados = df_recalc_edit[df_recalc_edit["Recalcular"]]["Código da Peça"].tolist()
                    linhas_recalculadas = []
                    
                    for _, row in df_ultimos[df_ultimos["Código da Peça"].isin(codigos_selecionados)].iterrows():
                        try:
                            row_clean = row.to_dict()
                            roteiro_raw = row_clean.get("Usinagem_JSON", "[]")
                            roteiro = json.loads(roteiro_raw) if isinstance(roteiro_raw, str) else []
                            
                            novo_custo_usinagem = 0.0
                            lote_recalc = max(1, safe_int(row_clean.get("Lote", 100)))
                            
                            if isinstance(roteiro, list):
                                for op in roteiro:
                                    pcs_h = max(0.1, safe_float(op.get("Peças por Hora"), 50.0))
                                    maq_nome = safe_str(op.get("Máquina"), "Outro")
                                    novo_custo_usinagem += (lote_recalc / pcs_h) * valores_maquinas.get(maq_nome, 120.0)
                                    op["Preço/Hora_Aplicado"] = valores_maquinas.get(maq_nome, 120.0)
                                row_clean["Usinagem_JSON"] = json.dumps(roteiro)
                            
                            custo_fabrica = safe_float(row_clean.get("Custo Material (R$)")) + novo_custo_usinagem + safe_float(row_clean.get("Custo Tratamento (R$)"))
                            fator_m = max(0.05, (1 - (safe_float(row_clean.get("Margem Lucro (%)", 30)) / 100)))
                            valor_venda = custo_fabrica / fator_m
                            imp_pct = safe_float(impostos.get("IR")) + safe_float(impostos.get("FS"))
                            preco_lote = valor_venda + (valor_venda * (imp_pct / 100))
                            
                            row_clean["Preço Total Lote (R$)"] = round(preco_lote, 2)
                            row_clean["Preço Unitário (R$)"] = round(preco_lote / lote_recalc, 2)
                            row_clean["Origem/Alteração"] = "Recálculo de Tarifas"
                            row_clean["Data/Hora"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                            
                            if "Recalcular" in row_clean: del row_clean["Recalcular"]
                            if "_dt_temp" in row_clean: del row_clean["_dt_temp"]
                            
                            linhas_recalculadas.append(row_clean)
                        except: pass
                        
                    if linhas_recalculadas:
                        df_final_salvar = pd.concat([df_init, pd.DataFrame(linhas_recalculadas)], ignore_index=True)
                        df_final_salvar.to_csv(ARQUIVO_HISTORICO, index=False)
                        st.session_state["msg_sucesso_aba4"] = f"✅ {len(linhas_recalculadas)} orçamentos recalculados com as novas tarifas!"
                        st.rerun()

    if st.session_state.get("msg_sucesso_aba4"):
        st.success(st.session_state["msg_sucesso_aba4"])
        st.session_state["msg_sucesso_aba4"] = ""

    st.markdown("---")
    st.subheader("🗑️ Zona de Perigo")
    if not df_init.empty:
        codigo_del = st.selectbox("Apagar histórico de um código específico:", [""] + lista_codigos)
        if codigo_del and st.button(f"Deletar todos os registros de {codigo_del}", type="primary"):
            df_init[df_init["Código da Peça"] != codigo_del].to_csv(ARQUIVO_HISTORICO, index=False)
            st.rerun()

# =============================================================================
# 🛒 TELA 5: COTAÇÃO FINAL (VENDAS)
# =============================================================================
elif opcao_menu == "🛒 5. Cotação Final":
    st.subheader("🛒 Módulo de Vendas (Simulador de Cotação)")
    st.write("Monte propostas comerciais simulando Lotes e Margens livremente. Salve e exporte para o cliente.")

    if df_init.empty:
        st.info("Nenhum orçamento disponível no banco de dados da engenharia.")
    else:
        # --- PASSO 1: O CARRINHO ---
        st.markdown("### Passo 1: Seleção do Cliente e Peças")
        cliente_cot = st.selectbox("Selecione o Cliente para cotar:", [""] + lista_empresas)

        if cliente_cot:
            df_cli = df_init[df_init["Empresa"] == cliente_cot].copy()
            df_cli['_dt'] = pd.to_datetime(df_cli["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
            df_ultimos = df_cli.sort_values("_dt").groupby("Código da Peça").last().reset_index()

            pecas_selecionadas = st.multiselect("Adicione as peças ao carrinho:", options=df_ultimos["Código da Peça"].tolist())

            if pecas_selecionadas:
                # --- PASSO 2: MESA DE NEGOCIAÇÃO ---
                st.markdown("---")
                st.markdown("### Passo 2: Mesa de Negociação")
                st.info("💡 Edite as colunas 'Novo Lote' e 'Margem Desejada (%)' para ajustar o preço da proposta.")
                
                dados_carrinho = []
                for _, row in df_ultimos[df_ultimos["Código da Peça"].isin(pecas_selecionadas)].iterrows():
                    r = row.to_dict()
                    lote_original = max(1, safe_int(r.get("Lote", 100)))
                    
                    custo_mat_unit = safe_float(r.get("Custo Material (R$)")) / lote_original
                    custo_trat_unit = safe_float(r.get("Custo Tratamento (R$)")) / lote_original
                    peso_unit = safe_float(r.get("Total Kg Lote")) / lote_original

                    roteiro_raw = r.get("Usinagem_JSON", "[]")
                    roteiro = json.loads(roteiro_raw) if isinstance(roteiro_raw, str) else []
                    custo_usi_unit = 0.0
                    if isinstance(roteiro, list):
                        for op in roteiro:
                            pcs_h = max(0.1, safe_float(op.get("Peças por Hora"), 50.0))
                            maq_nome = safe_str(op.get("Máquina"), "Outro")
                            taxa_hora = safe_float(op.get("Preço/Hora_Aplicado", st.session_state.valores_maquinas.get(maq_nome, 120.0)))
                            custo_usi_unit += (1 / pcs_h) * taxa_hora

                    custo_base_unit = custo_mat_unit + custo_trat_unit + custo_usi_unit

                    dados_carrinho.append({
                        "Código da Peça": r["Código da Peça"],
                        "Nome": safe_str(r.get("Nome da Peça", "")),
                        "Custo Base (R$)": custo_base_unit,
                        "Peso Unit. (Kg)": peso_unit,
                        "Novo Lote": lote_original,
                        "Margem Desejada (%)": safe_float(r.get("Margem Lucro (%)", 30))
                    })

                df_base_cotacao = pd.DataFrame(dados_carrinho)
                df_editado = st.data_editor(
                    df_base_cotacao,
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Código da Peça": st.column_config.TextColumn(disabled=True),
                        "Nome": st.column_config.TextColumn(disabled=True),
                        "Custo Base (R$)": st.column_config.NumberColumn("Custo Base (Não Editável)", format="R$ %.2f", disabled=True),
                        "Peso Unit. (Kg)": st.column_config.NumberColumn(format="%.3f kg", disabled=True),
                        "Novo Lote": st.column_config.NumberColumn(min_value=1, step=1),
                        "Margem Desejada (%)": st.column_config.NumberColumn(min_value=1.0, max_value=99.0, step=1.0)
                    }
                )

                # --- Motor de Vendas (Recálculo On the Fly) ---
                total_imposto_pct = safe_float(st.session_state.impostos.get("IR")) + safe_float(st.session_state.impostos.get("FS"))
                valor_total_cotacao, imposto_total_cotacao, custo_total_cotacao, peso_total_cotacao = 0.0, 0.0, 0.0, 0.0
                resultados_visuais = []

                for _, row in df_editado.iterrows():
                    lote = safe_int(row["Novo Lote"])
                    margem = safe_float(row["Margem Desejada (%)"])
                    custo_unit = safe_float(row["Custo Base (R$)"])
                    
                    peso_total_cotacao += safe_float(row["Peso Unit. (Kg)"]) * lote

                    custo_bruto_lote = custo_unit * lote
                    fator_lucro = max(0.01, (1 - (margem / 100)))
                    valor_sem_imposto = custo_bruto_lote / fator_lucro
                    imposto_reais = valor_sem_imposto * (total_imposto_pct / 100)
                    
                    preco_lote_final = valor_sem_imposto + imposto_reais
                    preco_unit_final = preco_lote_final / lote

                    valor_total_cotacao += preco_lote_final
                    imposto_total_cotacao += imposto_reais
                    custo_total_cotacao += custo_bruto_lote

                    resultados_visuais.append({
                        "Código": row["Código da Peça"], 
                        "Nome": row["Nome"], 
                        "Lote": lote,
                        "Preço de Venda Unitário": round(preco_unit_final, 2), 
                        "Total Faturado": round(preco_lote_final, 2)
                    })

                # --- PASSO 3: A PROPOSTA ---
                st.markdown("---")
                st.markdown("### Passo 3: A Proposta (Visão do Cliente)")
                df_resumo = pd.DataFrame(resultados_visuais)
                
                # Formatar a tabela visualmente (sem estragar os números para o Excel)
                df_resumo_formatado = df_resumo.copy()
                df_resumo_formatado["Preço de Venda Unitário"] = df_resumo_formatado["Preço de Venda Unitário"].apply(lambda x: f"R$ {x:.2f}")
                df_resumo_formatado["Total Faturado"] = df_resumo_formatado["Total Faturado"].apply(lambda x: f"R$ {x:.2f}")
                
                st.dataframe(df_resumo_formatado, hide_index=True, use_container_width=True)
                
                # --- PASSO 4: RAIO-X DA NEGOCIAÇÃO ---
                st.markdown("---")
                st.markdown("### 📊 Passo 4: Raio-X da Negociação (Visão Interna)")
                
                lucro_bruto_reais = valor_total_cotacao - custo_total_cotacao
                lucro_real_reais = lucro_bruto_reais - imposto_total_cotacao
                margem_bruta_pct = (lucro_bruto_reais / valor_total_cotacao * 100) if valor_total_cotacao > 0 else 0
                margem_real_pct = (lucro_real_reais / valor_total_cotacao * 100) if valor_total_cotacao > 0 else 0
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("1. Faturamento Total", f"R$ {valor_total_cotacao:.2f}")
                c2.metric("2. Custo de Fábrica", f"R$ {custo_total_cotacao:.2f}")
                c3.metric(f"3. Guias de Imposto ({total_imposto_pct}%)", f"R$ {imposto_total_cotacao:.2f}")
                c4.metric("4. Lucro Livre (Dinheiro no Bolso)", f"R$ {lucro_real_reais:.2f}")

                st.write("") # Espaçamento
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("5. Margem Bruta (%)", f"{margem_bruta_pct:.1f} %")
                c6.metric("6. Margem Líquida Real (%)", f"{margem_real_pct:.1f} %")
                c7.metric("7. Peso Total Estimado", f"{peso_total_cotacao:.2f} kg")
                c8.write("")
                
                st.markdown("---")
                
                # --- PASSO 5: AÇÕES FINAIS ---
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("💾 Salvar Cotação no Histórico", type="primary"):
                        ARQUIVO_COTACOES = "historico_cotacoes_vendas.csv"
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        
                        df_salvar_cot = df_resumo.copy()
                        df_salvar_cot["Data/Hora"] = agora
                        df_salvar_cot["Cliente"] = cliente_cot
                        df_salvar_cot["Faturamento Total Cotação"] = valor_total_cotacao
                        df_salvar_cot["Lucro Real (%)"] = margem_real_pct
                        
                        if os.path.exists(ARQUIVO_COTACOES):
                            try:
                                df_cot_antigo = pd.read_csv(ARQUIVO_COTACOES)
                                df_cot_final = pd.concat([df_cot_antigo, df_salvar_cot], ignore_index=True)
                            except:
                                df_cot_final = df_salvar_cot
                        else:
                            df_cot_final = df_salvar_cot
                            
                        df_cot_final.to_csv(ARQUIVO_COTACOES, index=False)
                        st.success("✅ Cotação salva com sucesso no banco de dados!")
                
                with col_btn2:
                    # Geração mágica do arquivo Excel na memória
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_resumo.to_excel(writer, sheet_name='Proposta Comercial', index=False)
                    
                    st.download_button(
                        label="📥 Exportar Proposta para Excel (.xlsx)",
                        data=buffer.getvalue(),
                        file_name=f"Cotacao_{cliente_cot}_{datetime.now().strftime('%d%m%Y')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
