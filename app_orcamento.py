import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# Configuração da página profissional
st.set_page_config(page_title="Sistema União - Orçamentos v2", page_icon="⚙️", layout="wide")

st.title("🛠️ Sistema União de Orçamentos & Recálculo em Massa")

# Nome do arquivo de banco de dados local
ARQUIVO_HISTORICO = "historico_orcamentos_estruturado.csv"

# Constantes fixas de materiais
DADOS_MATERIAIS = {
    "aço sx": 0.68, "aço red": 0.62, "aço quad": 0.72,
    "aluminio red": 0.212, "aluminio quad": 0.212, "aluminio sx": 0.212,
    "latao red": 0.68, "latao quad": 0.78, "latao sx": 0.72
}

# -----------------------------------------------------------------------------
# INTERFACE EM ABAS (Criação da Aba de Configurações solicitada)
# -----------------------------------------------------------------------------
aba_calculo, aba_historico, aba_config = st.tabs([
    "📊 1. Novo Orçamento", 
    "📜 2. Histórico & Preços Atuais", 
    "⚙️ 3. Configurações de Custos e Impostos"
])

# -----------------------------------------------------------------------------
# ABA 3: CONFIGURAÇÕES (Preço Hora-Máquina e Impostos que mudam raramente)
# -----------------------------------------------------------------------------
with aba_config:
    st.subheader("⚙️ Painel de Controle de Custos Fixos")
    st.write("Os valores definidos aqui serão aplicados em todos os novos cálculos e nos recálculos em massa.")
    
    col_cfg1, col_cfg2 = st.columns(2)
    
    with col_cfg1:
        st.markdown("#### 💰 Preço da Hora-Máquina (R$/hora)")
        # Inicializa ou mantém os valores na memória do navegador
        if "valores_maquinas" not in st.session_state:
            st.session_state.valores_maquinas = {
                "CNC": 150.0, "Torno Automático": 120.0, "Freza": 120.0,
                "Furadeira": 70.0, "Torno Revolver": 90.0, "Retífica": 150.0,
                "Serra": 70.0, "Montagem": 90.0, "Outro": 150.0
            }
        
        # Cria inputs dinâmicos para cada máquina
        maquinas_atualizadas = {}
        for maq, valor_padrao in st.session_state.valores_maquinas.items():
            maquinas_atualizadas[maq] = st.number_input(f"Taxa horária: {maq}", min_value=0.0, value=valor_padrao, step=5.0)
        st.session_state.valores_maquinas = maquinas_atualizadas

    with col_cfg2:
        st.markdown("#### 📝 Impostos (Simples Nacional)")
        ir_atual = st.number_input("Imposto de Renda / Alíquota Base (%)", min_value=0.0, value=6.0, step=0.5)
        fs_atual = st.number_input("Fundo Social / Encargos (%)", min_value=0.0, value=4.0, step=0.5)
        st.session_state.impostos = {"IR": ir_atual, "FS": fs_atual}
        
        st.caption("ℹ️ O ICMS está configurado como 0% por padrão devido ao regime tributário.")

# Recupera os valores da aba de configuração para usar no resto do sistema
valores_maquinas = st.session_state.valores_maquinas
impostos = st.session_state.impostos

# -----------------------------------------------------------------------------
# ABA 1: GERADOR DE CÁLCULO
# -----------------------------------------------------------------------------
if "dados_carregados" not in st.session_state:
    st.session_state.dados_carregados = None

with aba_calculo:
    # --- LINHA 1: DADOS DO CLIENTE ---
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    with col_cli1:
        empresa = st.text_input("Empresa/Cliente", value="", placeholder="Ex: TS")
    with col_cli2:
        comprador = st.text_input("Comprador Responsável", value="", placeholder="Ex: Guilherme")

    st.markdown("---")
    
    # --- LINHA 2: DADOS DO PRODUTO + BUSCA INTELIGENTE ---
    st.subheader("📦 Dados do Produto")
    col_prod1, col_prod2, col_prod3 = st.columns(3)
    
    with col_prod1:
        codigo_peca = st.text_input("Código da Peça", value="", placeholder="Ex: TS-8-030-XXXX")
        
        # Sistema de busca automática por histórico anterior
        if codigo_peca and os.path.exists(ARQUIVO_HISTORICO):
            df_hist_busca = pd.read_csv(ARQUIVO_HISTORICO)
            df_filtrado = df_hist_busca[df_hist_busca["Código da Peça"] == codigo_peca]
            if not df_filtrado.empty:
                st.info(f"🔍 Cotação anterior encontrada para o código {codigo_peca}!")
                if st.button("🔄 Carregar dados da última versão"):
                    st.session_state.dados_carregados = df_filtrado.iloc[-1].to_dict()
                    st.rerun()

    hist = st.session_state.dados_carregados if st.session_state.dados_carregados else {}
    
    with col_prod2:
        nome_peca = st.text_input("Nome da Peça", value=hist.get("Nome da Peça", ""))
    with col_prod3:
        lote = st.number_input("Quantidade do Lote", min_value=1, value=int(hist.get("Lote", 100)))

    col_prod4, col_prod5 = st.columns(2)
    with col_prod4:
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, value=float(hist.get("Comprimento (mm)", 0.0)))
    with col_prod5:
        margem_corte = st.number_input("Margem de Corte/Perda por peça (mm)", min_value=0.0, value=5.0)

    st.markdown("---")

    # --- SEÇÃO: MATÉRIA PRIMA ---
    st.subheader("🧱 Definição da Matéria-Prima")
    tipo_mp = st.selectbox("Como a Matéria-Prima será contabilizada?", 
                           ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Fornecido pelo Cliente (Mão de Obra Pura)"])
    
    custo_total_material = 0.0
    total_quilos = 0.0
    detalhes_material = ""

    col_mat1, col_mat2, col_mat3 = st.columns(3)
    
    with col_mat1:
        preco_unitario_mp = st.number_input("Preço Atual da MP (R$ por Kg, Metro ou Peça)", min_value=0.0, value=float(hist.get("Preço MP Unitário", 0.0)) if hist else 0.0, step=1.0)

    # Coleta de dados específicos com base no tipo de Matéria Prima
    if "Por Peso" in tipo_mp:
        with col_mat2:
            material_sel = st.selectbox("Selecione a Liga (Constante)", list(DADOS_MATERIAIS.keys()))
            constante = DADOS_MATERIAIS[material_sel]
        
        if tipo_mp == "Por Peso (Barra Maciça/Sextavada)":
            with col_mat3:
                diametro = st.number_input("Diâmetro da Barra (mm)", min_value=0.0, value=15.0)
            peso_por_metro = (diametro ** 2 * constante) / 100
        else: # Tubo
            with col_mat3:
                di_ext = st.number_input("Diâmetro Externo (mm)", min_value=0.0, value=20.0)
                di_int = st.number_input("Diâmetro Interno/Furo (mm)", min_value=0.0, value=10.0)
            peso_por_metro = ((di_ext ** 2) - (di_int ** 2)) * constante / 100

        total_metros = ((comprimento + margem_corte) * lote) / 1000
        total_quilos = total_metros * peso_por_metro
        custo_total_material = total_quilos * preco_unitario_mp
        detalhes_material = f"{total_quilos:.2f} kg de {material_sel}"

    elif tipo_mp == "Por Metro Linear":
        total_metros = ((comprimento + margem_corte) * lote) / 1000
        custo_total_material = total_metros * preco_unitario_mp
        detalhes_material = f"{total_metros:.2f} m"
        # Pede peso estimado para o tratamento por kg funcionar
        with col_mat2:
            peso_est = st.number_input("Peso total estimado do lote (kg) [Para Tratamento]", min_value=0.1, value=10.0)
            total_quilos = peso_est

    elif tipo_mp == "Por Peça Pronta" or tipo_mp == "Fornecido pelo Cliente (Mão de Obra Pura)":
        custo_total_material = 0.0 if "Fornecido" in tipo_mp else (lote * preco_unitario_mp)
        detalhes_material = "Fornecido pelo Cliente" if "Fornecido" in tipo_mp else f"{lote} Peças base"
        with col_mat2:
            peso_est = st.number_input("Peso total estimado do lote (kg) [Para Tratamento]", min_value=0.1, value=10.0)
            total_quilos = peso_est

    st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}", help=f"Peso total considerado: {total_quilos:.2f} kg")
    st.markdown("---")

    # --- SEÇÃO: USINAGEM DINÂMICA ---
    st.subheader("🔨 Roteiro de Processos de Usinagem")
    
    # Recupera roteiro antigo se houver, ou cria padrão
    if hist and "Usinagem_JSON" in hist:
        try:
            default_rows = json.loads(hist["Usinagem_JSON"])
        except:
            default_rows = [{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50}]
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
        key="editor_usinagem"
    )

    custo_total_usinagem = 0.0
    for idx, row in df_usinagem_input.iterrows():
        try:
            custo_total_usinagem += (lote / row["Peças por Hora"]) * valores_maquinas.get(row["Máquina"], 120.0)
        except:
            pass

    st.caption(f"💰 Custo de Usinagem Calculado com as taxas vigentes: **R$ {custo_total_usinagem:.2f}**")
    st.markdown("---")

    # --- SEÇÃO: TRATAMENTO POR KG (Ajuste solicitado) ---
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
        key="editor_tratamentos"
    )

    # Cálculo do custo baseado no peso total em kg do lote
    soma_preco_kg_tratamento = 0.0
    for idx, row in df_trat_input.iterrows():
        try:
            soma_preco_kg_tratamento += row["Preço por Kg (R$)"]
        except:
            pass
    custo_total_tratamentos = soma_preco_kg_tratamento * total_quilos
    st.caption(f"✨ Custo total de tratamento para os {total_quilos:.2f} kg: **R$ {custo_total_tratamentos:.2f}**")
    st.markdown("---")

    # --- SEÇÃO FINANCEIRA (Ajuste de limites de margem 15% a 100%) ---
    st.subheader("📈 Margem de Lucro e Fechamento")
    porcentagem_lucro = st.slider("Selecione a Margem de Lucro desejada (%)", min_value=15, max_value=95, value=30, step=5, 
                                  help="Margem calculada por dentro. Limitada a 95% matematicamente para evitar divisões incorretas.")

    # --- FÓRMULAS OFICIAIS DO SEU EXCEL ---
    custo_bruto_total = custo_total_material + custo_total_usinagem + custo_total_tratamentos
    
    # Margem por dentro: Custo / (1 - Margem)
    valor_com_lucro = custo_bruto_total / (1 - (porcentagem_lucro / 100))
    lucro_bruto_real = valor_com_lucro - custo_bruto_total
    
    # Impostos da aba de configurações
    total_imposto_pct = impostos["IR"] + impostos["FS"]
    valor_impostos = valor_com_lucro * (total_imposto_pct / 100)
    
    preco_venda_lote = valor_com_lucro + valor_impostos
    preco_unitario_final = preco_venda_lote / lote if lote > 0 else 0.0

    st.markdown("### 📋 Resumo Controlado da Proposta")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo de Fábrica Total", f"R$ {custo_bruto_total:.2f}")
    c2.metric(f"Lucro Bruto ({porcentagem_lucro}%)", f"R$ {lucro_bruto_real:.2f}")
    c3.metric(f"Impostos ({total_imposto_pct}%)", f"R$ {valor_impostos:.2f}")
    c4.metric("Preço UNITÁRIO Final", f"R$ {preco_unitario_final:.2f}")

    # --- SALVAR REGISTRO ---
    if st.button("💾 Gravar no Histórico", type="primary"):
        # Converte as tabelas dinâmicas em texto puro JSON para arquivar de forma segura
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
        st.success("✅ Cotação salva! Registrada no histórico e disponível para consultas futuras.")
        st.session_state.dados_carregados = None

# -----------------------------------------------------------------------------
# ABA 2: HISTÓRICO COMPLETO & CEREJA DO BOLO (RECÁLCULO EM MASSA)
# -----------------------------------------------------------------------------
with aba_historico:
    if not os.path.exists(ARQUIVO_HISTORICO):
        st.info("Nenhum orçamento gerado ainda no sistema.")
    else:
        df_completo = pd.read_csv(ARQUIVO_HISTORICO)
        
        opcao_visao = st.radio("Selecione a visualização dos dados:", ["🎯 Preços Atuais (Última Versão por Peça/Empresa)", "⏳ Histórico de Alterações Completo"])
        
        # Função interna que faz o milagre do recálculo em massa usando as configurações vigentes
        def processar_recalculo(dataframe_base):
            linhas_recalculadas = []
            for _, row in dataframe_base.iterrows():
                try:
                    # Extrai o roteiro de usinagem salvo em formato JSON
                    roteiro = json.loads(row["Usinagem_JSON"])
                    novo_custo_usinagem = 0.0
                    for op in roteiro:
                        # Recalcula usando os valores atuais da aba de configurações!
                        novo_custo_usinagem += (row["Lote"] / op["Peças por Hora"]) * valores_maquinas.get(op["Máquina"], 120.0)
                    
                    # Reconstrói a matemática do orçamento com os impostos vigentes
                    c_material = row["Custo Material (R$)"]
                    c_tratamento = row["Custo Tratamento (R$)"]
                    custo_fabrica_novo = c_material + novo_custo_usinagem + c_tratamento
                    
                    valor_lucro_novo = custo_fabrica_novo / (1 - (row["Margem Lucro (%)"] / 100))
                    total_imp_pct = impostos["IR"] + impostos["FS"]
                    impostos_novos = valor_lucro_novo * (total_imp_pct / 100)
                    
                    preco_lote_novo = valor_lucro_novo + impostos_novos
                    preco_unit_novo = preco_lote_novo / row["Lote"]
                    
                    linhas_recalculadas.append({
                        "Empresa/Cliente": row["Empresa"],
                        "Código da Peça": row["Código da Peça"],
                        "Nome da Peça": row["Nome da Peça"],
                        "Lote": row["Lote"],
                        "Custo Mat. Prima (R$)": c_material,
                        "Novo Custo Usinagem (R$)": round(novo_custo_usinagem, 2),
                        "Custo Tratamento (R$)": c_tratamento,
                        "Preço Total Anterior (R$)": "Consultar Histórico",
                        "NOVO Preço Total Lote (R$)": round(preco_lote_novo, 2),
                        "NOVO Preço Unitário (R$)": round(preco_unit_novo, 2)
                    })
                except:
                    pass
            return pd.DataFrame(linhas_recalculadas)

        if opcao_visao == "⏳ Histórico de Alterações Completo":
            st.subheader("📋 Registro Cronológico de Cotações")
            st.dataframe(df_completo.iloc[::-1], use_container_width=True)
            
        else:
            st.subheader("🎯 Tabela de Preços Atuais (Última versão de cada código)")
            
            # Filtra para obter apenas o último registro de cada código de peça (Preço Atual)
            df_ultimos_preços = df_completo.sort_values("Data/Hora").groupby("Código da Peça").last().reset_index()
            
            # Ordena por empresa/cliente para ficar organizado conforme solicitado
            df_ultimos_preços = df_ultimos_preços.sort_values(by="Empresa")
            
            # Exibe os dados originais básicos
            st.dataframe(df_ultimos_preços[["Empresa", "Código da Peça", "Nome da Peça", "Lote", "Custo Material (R$)", "Custo Tratamento (R$)"]], use_container_width=True)
            
            st.markdown("### 🍒 A Cereja do Bolo: Atualização de Tarifas em Massa")
            st.write("Mudou os preços das máquinas ou impostos na Aba 3? Clique no botão abaixo para gerar instantaneamente a tabela de preços corrigida de todos os clientes ao mesmo tempo.")
            
            if st.button("🔄 Recalcular Todos os Preços Atuais Simultaneamente", type="primary"):
                df_atualizado = processar_recalculo(df_ultimos_preços)
                
                if not df_atualizado.empty:
                    st.success("🚀 Todos os preços foram recalculados em tempo real com sucesso!")
                    # Mostra a tabela simulada novinha em folha
                    st.dataframe(df_atualizado, use_container_width=True)
                    
                    # Permite baixar a tabela nova direto para enviar aos clientes ou abrir no Excel
                    csv_export = df_atualizado.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Nova Tabela Geral Atualizada (Excel)", data=csv_export, file_name="nova_tabela_preços_usinagem.csv", mime="text/csv")
                else:
                    st.warning("Não foi possível recalcular. Verifique se os dados contêm roteiros válidos.")
