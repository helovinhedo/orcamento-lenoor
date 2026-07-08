import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import io

# =============================================================================
# 🧱 1. CONFIGURAÇÕES INICIAIS E FUNÇÕES UTILITÁRIAS
# =============================================================================
st.set_page_config(page_title="Sistema Lenoor - Orçamentos", page_icon="⚙️", layout="wide")

ARQUIVO_HISTORICO = "historico_orcamentos_estruturado.csv"
ARQUIVO_CONFIG = "config_lenoor.json"  

# Valores padrão de fábrica caso o JSON não exista
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

# Funções de conversão segura
def safe_float(val, default=0.0):
    try: return default if pd.isna(val) or val is None else float(val)
    except: return default

def safe_int(val, default=0):
    try: return default if pd.isna(val) or val is None else int(float(val))
    except: return default

def safe_str(val, default=""):
    return default if pd.isna(val) or val is None else str(val).strip()

# Leitura/Gravação de Configurações
def ler_config_permanente():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r") as f:
                dados = json.load(f)
                # Garante que chaves antigas não quebrem o sistema novo
                if "materiais" not in dados: dados["materiais"] = DEFAULTS_MATERIAIS
                return dados
        except: pass
    return {"valores_maquinas": DEFAULTS_MAQUINAS, "impostos": DEFAULTS_IMPOSTOS, "materiais": DEFAULTS_MATERIAIS}

def salvar_config_permanente(maquinas, impostos, materiais):
    try:
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump({"valores_maquinas": maquinas, "impostos": impostos, "materiais": materiais}, f, indent=4)
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
    except:
        return pd.DataFrame(columns=COLUNAS_PADRAO)

# =============================================================================
# 🧠 2. INICIALIZAÇÃO CONTROLADA DE VARIÁVEIS DE SESSÃO
# =============================================================================
config_carregada = ler_config_permanente()

if "valores_maquinas" not in st.session_state: st.session_state.valores_maquinas = config_carregada["valores_maquinas"]
if "impostos" not in st.session_state: st.session_state.impostos = config_carregada["impostos"]
if "materiais" not in st.session_state: st.session_state.materiais = config_carregada["materiais"]

if "menu_anterior" not in st.session_state: st.session_state.menu_anterior = ""
if "editor_version" not in st.session_state: st.session_state.editor_version = 0  
if "taxas_original_msg" not in st.session_state: st.session_state["taxas_original_msg"] = ""

# Correção BUG 1 (KeyError): Todas as chaves mapeadas explicitamente
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

if "df_usinagem_v3" not in st.session_state:
    st.session_state["df_usinagem_v3"] = pd.DataFrame([{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50.0}])
if "df_tratamento_v3" not in st.session_state:
    st.session_state["df_tratamento_v3"] = pd.DataFrame([{"Tratamento": "Nenhum", "Preço por Kg (R$)": 0.0}])

# Listas do histórico
lista_empresas = []
lista_codigos = []
df_init = ler_historico_seguro()

if not df_init.empty:
    lista_empresas = sorted(df_init["Empresa"].dropna().astype(str).unique().tolist())
    empresa_atual = st.session_state.get("sel_empresa_aba1", "")
    if empresa_atual and empresa_atual != "➕ Novo Cliente...":
        lista_codigos = sorted(df_init[df_init["Empresa"] == empresa_atual]["Código da Peça"].dropna().astype(str).unique().tolist())
    else:
        lista_codigos = sorted(df_init["Código da Peça"].dropna().astype(str).unique().tolist())

# Callback Auto-Complete
def carregar_roteiro_antigo_callback():
    codigo_target = st.session_state.get("sel_codigo_peca", "")
    if codigo_target and codigo_target != "➕ Novo Código...":
        try:
            df_hist = ler_historico_seguro()
            df_filtrado = df_hist[df_hist["Código da Peça"] == codigo_target]
            
            if not df_filtrado.empty:
                df_filtrado = df_filtrado.copy()
                df_filtrado['_dt_temp'] = pd.to_datetime(df_filtrado["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
                last_hist = df_filtrado.sort_values('_dt_temp').iloc[-1].fillna("").to_dict()
                
                st.session_state["sel_empresa_aba1"] = safe_str(last_hist.get("Empresa"))
                st.session_state["txt_comprador"] = safe_str(last_hist.get("Comprador"))
                st.session_state["txt_nome_peca"] = safe_str(last_hist.get("Nome da Peça"))
                st.session_state["num_lote"] = max(1, safe_int(last_hist.get("Lote", 100)))
                st.session_state["num_comprimento"] = max(0.0, safe_float(last_hist.get("Comprimento (mm)")))
                st.session_state["num_margem_corte"] = max(0.0, safe_float(last_hist.get("Margem Corte (mm)", 5.0)))
                st.session_state["sel_tipo_mp"] = safe_str(last_hist.get("Tipo MP", "Por Peso (Barra Maciça/Sextavada)"))
                
                # Puxa o preço do material salvo na base de configurações, se for por peso, ou do histórico
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
                        st.session_state["taxas_original_msg"] = f"Últimas taxas de máquina aplicadas: {resumo}"
                    else: st.session_state["taxas_original_msg"] = ""
                    
                    st.session_state["df_usinagem_v3"] = df_usi[["Operação", "Máquina", "Peças por Hora"]].copy()
                
                if "Tratamento_JSON" in last_hist and safe_str(last_hist["Tratamento_JSON"]) not in ["", "[]"]:
                    df_trat = pd.read_json(io.StringIO(str(last_hist["Tratamento_JSON"])))
                    st.session_state["df_tratamento_v3"] = df_trat[["Tratamento", "Preço por Kg (R$)"]].copy()
                    
                st.session_state.editor_version += 1
        except Exception as e:
            st.toast(f"Erro no autocomplete: {e}", icon="⚠️")

valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos
materiais = st.session_state.materiais

# =============================================================================
# 🧭 3. NAVEGAÇÃO LATERAL
# =============================================================================
st.sidebar.title("🧭 Menu Lenoor")
opcao_menu = st.sidebar.radio(
    "Navegação:",
    ["📊 1. Novo Orçamento", "📜 2. Histórico de Peças", "🧱 3. Matéria-Prima", "⚙️ 4. Custos Fixos & BD"]
)
st.sidebar.markdown("---")

if opcao_menu != st.session_state.menu_anterior:
    st.session_state["taxas_original_msg"] = ""
    st.session_state.menu_anterior = opcao_menu

# Alteração Estética: Título Limpo
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
        
        if empresa_sel == "➕ Novo Cliente...":
            empresa = st.text_input("Novo Cliente", placeholder="Ex: TS", key="txt_nova_empresa").strip()
        else: empresa = empresa_sel
            
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
            codigo_peca = st.text_input("Novo Código:", value=st.session_state["txt_novo_codigo"])
            st.session_state["txt_novo_codigo"] = codigo_peca
        else: codigo_peca = codigo_sel

    with col_cod_linha2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True) 
        if codigo_sel and codigo_sel != "➕ Novo Código...":
            # Alteração Estética: Botão Primary sem ícone
            st.button("Completar Dados", type="primary", use_container_width=True, on_click=carregar_roteiro_antigo_callback)

    if st.session_state["taxas_original_msg"]:
        st.info(st.session_state["taxas_original_msg"])

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
    
    custo_total_material, total_quilos, preco_unitario_mp = 0.0, 0.0, 0.0
    material_sel, diametro, di_ext, di_int = "N/A", 0.0, 0.0, 0.0

    if tipo_mp == "Mão de Obra Pura (Fornecido)":
        total_quilos = st.number_input("Peso total lote (kg) [Para Tratamento]", min_value=0.0, step=0.1, value=float(st.session_state["num_peso_fornecido"]))
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
                    di_ext = st.number_input("Diâmetro Ext. (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_di_ext"]))
                    di_int = st.number_input("Diâmetro Int. (mm)", min_value=0.0, step=0.1, value=float(st.session_state["num_di_int"]))
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
    # Correção BUG 3: key estática e fim da retroalimentação forçada
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
    # Correção BUG 2: Aceita decimais, passo 0.01, formato visual R$
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

    # --- FECHAMENTO ---
    porcentagem_lucro = st.slider("Margem de Lucro (%)", 15, 95, int(st.session_state["slider_lucro_aba1"]), 5)
    st.session_state["slider_lucro_aba1"] = porcentagem_lucro

    custo_bruto = custo_total_material + custo_total_usinagem + custo_total_tratamentos
    fator_lucro = max(0.05, (1 - (porcentagem_lucro / 100)))
        
    valor_venda_bruto = custo_bruto / fator_lucro
    lucro_real = valor_venda_bruto - custo_bruto
    total_imp_pct = safe_float(impostos.get("IR")) + safe_float(impostos.get("FS"))
    valor_impostos = valor_venda_bruto * (total_imp_pct / 100)
    preco_lote = valor_venda_bruto + valor_impostos
    preco_unit = preco_lote / lote if lote > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo de Fábrica", f"R$ {custo_bruto:.2f}")
    c2.metric("Lucro Bruto", f"R$ {lucro_real:.2f}")
    c3.metric(f"Impostos ({total_imp_pct}%)", f"R$ {valor_impostos:.2f}")
    c4.metric("Preço UNITÁRIO", f"R$ {preco_unit:.2f}")

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
                "Preço Unitário (R$)": round(preco_unit, 2),
                "Usinagem_JSON": df_usi_salvar.to_json(orient='records'),
                "Tratamento_JSON": df_trat_input.to_json(orient='records')
            }
            
            df_final = pd.concat([df_init, pd.DataFrame([novo_registro])], ignore_index=True) if not df_init.empty else pd.DataFrame([novo_registro])
            df_final.to_csv(ARQUIVO_HISTORICO, index=False)
            st.toast("✅ Gravado com Sucesso!")
            st.session_state.editor_version += 1
            st.rerun()

# =============================================================================
# 📜 TELA 2: HISTÓRICO
# =============================================================================
elif opcao_menu == "📜 2. Histórico de Peças":
    if df_init.empty: st.info("Nenhum orçamento gerado.")
    else:
        cliente_filtro = st.multiselect("🔍 Filtrar Cliente:", options=lista_empresas)
        opcao_visao = st.radio("Visualização:", ["🎯 Preços Atuais (Última Versão)", "⏳ Histórico Completo"])
        
        df_ord = df_init.copy()
        df_ord['_dt'] = pd.to_datetime(df_ord["Data/Hora"], format="%d/%m/%Y %H:%M", errors='coerce')
        df_ord = df_ord.sort_values("_dt", ascending=True)
        if cliente_filtro: df_ord = df_ord[df_ord["Empresa"].isin(cliente_filtro)]

        cols = ["Data/Hora", "Origem/Alteração", "Empresa", "Código da Peça", "Nome da Peça", "Lote", "Preço Unitário (R$)", "Preço Total Lote (R$)"]
        for c in cols: 
            if c not in df_ord.columns: df_ord[c] = "N/A"
        
        if "Completo" in opcao_visao: st.dataframe(df_ord[cols].iloc[::-1], use_container_width=True)
        else:
            df_ult = df_ord.groupby("Código da Peça").last().reset_index().sort_values("Empresa")
            st.dataframe(df_ult[["Empresa", "Código da Peça", "Nome da Peça", "Lote", "Preço Unitário (R$)", "Preço Total Lote (R$)"]], use_container_width=True)

# =============================================================================
# 🧱 TELA 3: GESTÃO DE MATÉRIA-PRIMA
# =============================================================================
elif opcao_menu == "🧱 3. Matéria-Prima":
    st.write("Atualize o preço do Kg das ligas. Ao salvar, a data será atualizada automaticamente.")
    
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
        
        for _, row in df_mat_edit.iterrows():
            liga = row["Liga"]
            preco_novo = float(row["Preço Atual (R$/Kg)"])
            preco_antigo = materiais[liga]["preco_atual"]
            data = hoje if preco_novo != preco_antigo else materiais[liga]["data_cotacao"]
            if preco_novo != preco_antigo: mudancas = True
            
            novos_materiais[liga] = {"constante": float(row["constante"]), "preco_atual": preco_novo, "data_cotacao": data}
            
        if mudancas:
            st.session_state.materiais = novos_materiais
            salvar_config_permanente(valores_maquinas, impostos, novos_materiais)
            st.toast("✅ Preços atualizados!")
            st.rerun()
        else: st.info("Nenhuma alteração detectada.")
    
    st.markdown("---")
    st.subheader("🔄 Recalcular Orçamentos por Material (Em Breve)")
    st.info("Aqui entrará a função de selecionar um material e recalcular automaticamente todas as peças afetadas.")

# =============================================================================
# ⚙️ TELA 4: CUSTOS FIXOS E BD
# =============================================================================
elif opcao_menu == "⚙️ 4. Custos Fixos & BD":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💰 Hora-Máquina (R$/h)")
        novas_maq = {maq: st.number_input(maq, min_value=0.0, value=safe_float(v), step=5.0) for maq, v in valores_maquinas.items()}
    with c2:
        st.markdown("#### 📝 Impostos (%)")
        novo_imp = {
            "IR": st.number_input("IR / Simples", 0.0, safe_float(impostos.get("IR", 6.0)), 0.5),
            "FS": st.number_input("Encargos Sociais", 0.0, safe_float(impostos.get("FS", 4.0)), 0.5)
        }

    if st.button("💾 Salvar Taxas Fixas", type="primary"):
        st.session_state.valores_maquinas, st.session_state.impostos = novas_maq, novo_imp
        salvar_config_permanente(novas_maq, novo_imp, materiais)
        st.toast("✅ Salvo!")
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Limpeza de Banco de Dados")
    if not df_init.empty:
        codigo_del = st.selectbox("Apagar histórico de um código específico:", [""] + lista_codigos)
        if codigo_del and st.button(f"Deletar {codigo_del}", type="primary"):
            df_init[df_init["Código da Peça"] != codigo_del].to_csv(ARQUIVO_HISTORICO, index=False)
            st.rerun()
