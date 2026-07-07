import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuração da página profissional
st.set_page_config(page_title="Orçamentos de Usinagem Inteligente", page_icon="⚙️", layout="wide")

st.title("🛠️ Sistema União de Orçamentos")
st.write("Gere cotações complexas de forma simples, sem risco de quebrar fórmulas.")

# -----------------------------------------------------------------------------
# 1. BANCO DE DADOS BASE (CONSTANTES E PREÇOS HORA-MÁQUINA)
# -----------------------------------------------------------------------------
DADOS_MATERIAIS = {
    "aço sx": 0.68, "aço red": 0.62, "aço quad": 0.72,
    "aluminio red": 0.212, "aluminio quad": 0.212, "aluminio sx": 0.212,
    "latao red": 0.68, "latao quad": 0.78, "latao sx": 0.72
}

# Preços padrão que podem ser editados na barra lateral
st.sidebar.header("⚙️ Configuração de Preço/Hora Máquina")
valores_maquinas = {
    "CNC": st.sidebar.number_input("CNC (R$/h)", value=150.0),
    "Torno Automático": st.sidebar.number_input("Torno Automático (R$/h)", value=120.0),
    "Freza": st.sidebar.number_input("Freza (R$/h)", value=120.0),
    "Furadeira": st.sidebar.number_input("Furadeira (R$/h)", value=70.0),
    "Torno Revolver": st.sidebar.number_input("Torno Revolver (R$/h)", value=90.0),
    "Retífica": st.sidebar.number_input("Retífica (R$/h)", value=150.0),
    "Serra": st.sidebar.number_input("Serra (R$/h)", value=70.0),
    "Montagem": st.sidebar.number_input("Montagem (R$/h)", value=90.0),
    "Outro": st.sidebar.number_input("Outro (R$/h)", value=150.0)
}

# Nome do arquivo de histórico
ARQUIVO_HISTORICO = "historico_orcamentos_completo.csv"

# -----------------------------------------------------------------------------
# 2. SISTEMA DE BUSCA INTELIGENTE POR HISTÓRICO
# -----------------------------------------------------------------------------
if "dados_carregados" not in st.session_state:
    st.session_state.dados_carregados = None

def buscar_ultimo_orcamento(codigo):
    if os.path.exists(ARQUIVO_HISTORICO):
        df = pd.read_csv(ARQUIVO_HISTORICO)
        # Filtra pelo código e pega o mais recente (último da lista)
        df_filtrado = df[df["Código da Peça"] == codigo]
        if not df_filtrado.empty:
            return df_filtrado.iloc[-1].to_dict()
    return None

# Criando as Abas principais do App
aba_calculo, aba_historico = st.tabs(["📊 Calcular Cotação", "📜 Histórico Geral"])

with aba_calculo:
    # --- LINHA 1: DADOS DO CLIENTE ---
    st.subheader("👤 Dados do Cliente")
    col_cli1, col_cli2 = st.columns(2)
    with col_cli1:
        empresa = st.text_input("Empresa", value="", placeholder="Ex: TS")
    with col_cli2:
        comprador = st.text_input("Comprador", value="", placeholder="Ex: Guilherme")

    st.markdown("---")
    
    # --- LINHA 2 & 3: DADOS DO PRODUTO + INTEGRAÇÃO HISTÓRICO ---
    st.subheader("📦 Dados do Produto")
    col_prod1, col_prod2, col_prod3 = st.columns(3)
    
    with col_prod1:
        codigo_peca = st.text_input("Código da Peça", value="", placeholder="Ex: TS-8-030-11358")
        
        # Gatilho de busca histórica automática ao digitar o código
        if codigo_peca:
            ultimo_registro = buscar_ultimo_orcamento(codigo_peca)
            if ultimo_registro:
                st.info(f"🔍 Encontrei uma cotação anterior para o código {codigo_peca}!")
                if st.button("🔄 Carregar dados desta última cotação"):
                    st.session_state.dados_carregados = ultimo_registro
                    st.rerun()

    # Se o usuário clicou para carregar, preenchemos com os dados antigos, senão vazios/padrão
    hist = st.session_state.dados_carregados if st.session_state.dados_carregados else {}
    
    with col_prod2:
        nome_peca = st.text_input("Nome da Peça", value=hist.get("Nome da Peça", ""))
    with col_prod3:
        lote = st.number_input("Quantidade do Lote", min_value=1, value=int(hist.get("Lote", 100)))

    col_prod4, col_prod5 = st.columns(2)
    with col_prod4:
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, value=float(hist.get("Comprimento (mm)", 0.0)))
    with col_prod5:
        # Planilhas de usinagem costumam ter uma perda fixa por corte de serra/faceamento (Ex: 5mm)
        margem_corte = st.number_input("Margem de Corte/Perda por peça (mm)", min_value=0.0, value=5.0, help="Soma ao comprimento para calcular a matéria-prima real.")

    st.markdown("---")

    # --- SEÇÃO: MATÉRIA PRIMA (DINÂMICA) ---
    st.subheader("🧱 Tipo de Matéria-Prima")
    
    tipo_mp = st.selectbox("Como a Matéria-Prima será contabilizada?", 
                           ["Por Peso (Barra Maciça/Sextavada)", "Por Peso (Tubo/Bucha)", "Por Metro Linear", "Por Peça Pronta", "Fornecido pelo Cliente (Mão de Obra Pura)"])
    
    custo_total_material = 0.0
    detalhes_material = ""

    if tipo_mp == "Fornecido pelo Cliente (Mão de Obra Pura)":
        st.success("ℹ️ Material fornecido pelo parceiro. Custo de Matéria-Prima definido como R$ 0,00.")
        custo_total_material = 0.0
        detalhes_material = "Fornecido pelo Cliente"
    else:
        col_mat1, col_mat2, col_mat3 = st.columns(3)
        with col_mat1:
            preco_unitario_mp = st.number_input("Preço Atual da MP (R$ por Kg, Metro ou Peça)", min_value=0.0, value=0.0, step=0.5)

        if "Por Peso" in tipo_mp:
            with col_mat2:
                material_sel = st.selectbox("Selecione a Liga (para Constante)", list(DADOS_MATERIAIS.keys()))
                constante = DADOS_MATERIAIS[material_sel]
            
            if tipo_mp == "Por Peso (Barra Maciça/Sextavada)":
                with col_mat3:
                    diametro = st.number_input("Diâmetro da Barra (mm)", min_value=0.0, value=0.0)
                # Fórmula decifrada do Excel: Peso/m = (D² * Constante) / 100
                peso_por_metro = (diametro ** 2 * constante) / 100
            
            elif tipo_mp == "Por Peso (Tubo/Bucha)":
                with col_mat3:
                    di_ext = st.number_input("Diâmetro Externo (mm)", min_value=0.0, value=0.0)
                    di_int = st.number_input("Diâmetro Interno/Furo (mm)", min_value=0.0, value=0.0)
                # Matemática de Tubos: Barra Externa menos o miolo interno
                peso_por_metro = ((di_ext ** 2) - (di_int ** 2)) * constante / 100

            # Cálculo de Metragem e Peso Total do lote considerando o corte
            total_metros = ((comprimento + margem_corte) * lote) / 1000
            total_quilos = total_metros * peso_por_metro
            custo_total_material = total_quilos * preco_unitario_mp
            detalhes_material = f"{total_quilos:.2f} kg de {material_sel}"
            
            st.metric("Custo Total Estimado da Matéria-Prima", f"R$ {custo_total_material:.2f}", help=f"Total de {total_quilos:.2f} kg necessários para o lote.")

        elif tipo_mp == "Por Metro Linear":
            total_metros = ((comprimento + margem_corte) * lote) / 1000
            custo_total_material = total_metros * preco_unitario_mp
            detalhes_material = f"{total_metros:.2f} Metros Lineares"
            st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}")

        elif tipo_mp == "Por Peça Pronta":
            custo_total_material = lote * preco_unitario_mp
            detalhes_material = f"{lote} Peças Base de terceiros"
            st.metric("Custo Total da Matéria-Prima", f"R$ {custo_total_material:.2f}")

    st.markdown("---")

    # --- SEÇÃO: CUSTO DE USINAGEM (LINHAS INFINITAS) ---
    st.subheader("🔨 Processos de Usinagem / Operações")
    st.write("Clique duas vezes em uma célula para editar. Use o botão **➕ (no final da tabela)** para adicionar novas operações.")
    
    # Criando estrutura inicial para a tabela de usinagem dinâmica
    default_rows = [{"Operação": "Tornear", "Máquina": "Torno Automático", "Peças por Hora": 50}]
    df_usinagem_input = st.data_editor(
        pd.DataFrame(default_rows),
        num_rows="dynamic", # Permite adicionar linhas infinitas!
        column_config={
            "Operação": st.column_config.TextColumn("Nome da Operação (Ex: Facear, Furar)", required=True),
            "Máquina": st.column_config.SelectboxColumn("Máquina utilizada", options=list(valores_maquinas.keys()), required=True),
            "Peças por Hora": st.column_config.NumberColumn("Produção (Peças/Hora)", min_value=1, default=50, required=True)
        },
        use_container_width=True,
        key="tabela_usinagem"
    )

    # Cálculo do custo total das linhas de usinagem
    custo_total_usinagem = 0.0
    for index, row in df_usinagem_input.iterrows():
        try:
            maq = row["Máquina"]
            prod_hora = row["Peças por Hora"]
            preco_hora_maq = valores_maquinas.get(maq, 120.0)
            
            # Horas necessárias para o lote nesta operação = lote / produção por hora
            horas_operacao = lote / prod_hora
            custo_linha = horas_operacao * preco_hora_maq
            custo_total_usinagem += custo_linha
        except:
            pass # Previne erros caso a linha esteja sendo digitada ainda

    st.caption(f"💰 Custo acumulado de Mão de Obra / Usinagem: **R$ {custo_total_usinagem:.2f}**")

    st.markdown("---")

    # --- SEÇÃO: TRATAMENTOS SUPERFICIAIS (OPCIONAL) ---
    st.subheader("✨ Tratamentos Superficiais / Térmicos (Opcional)")
    st.write("Ex: Bicromatizado, Nitretação, Zinco, etc. Se não houver, deixe em branco ou apague as linhas.")
    
    default_trat = [{"Tratamento": "Nenhum / Sem Tratamento", "Preço por Peça (R$)": 0.0}]
    df_trat_input = st.data_editor(
        pd.DataFrame(default_trat),
        num_rows="dynamic",
        column_config={
            "Tratamento": st.column_config.TextColumn("Descrição do Tratamento", required=True),
            "Preço por Peça (R$)": st.column_config.NumberColumn("Custo unitário", min_value=0.0, default=0.0)
        },
        use_container_width=True,
        key="tabela_tratamentos"
    )

    custo_total_tratamentos = 0.0
    for index, row in df_trat_input.iterrows():
        try:
            custo_total_tratamentos += (row["Preço por Peça (R$)"] * lote)
        except:
            pass

    st.markdown("---")

    # --- SEÇÃO: FECHAMENTO FINANCEIRO & IMPOSTOS ---
    st.subheader("📈 Margem de Lucro e Impostos (Simples Nacional)")
    
    col_fin1, col_fin2 = st.columns(2)
    with col_fin1:
        # Controle total do % de Lucro desejado
        porcentagem_lucro = st.slider("Defina a Margem de Lucro desejada (%)", min_value=0, max_value=200, value=30, step=5)
    
    with col_fin2:
        st.write("**Alíquotas consideradas (Empresa do Simples):**")
        st.text("▪️ % IR + Contribuições: Incluso no Simples")
        st.text("▪️ % FS (Fundo Social / Encargos): Incluso na Mão de Obra")
        st.text("▪️ % ICMS: 0% (Optante do Simples Nacional / Sem destaque)")

    # --- CÁLCULO FINAL ---
    custo_bruto_total = custo_total_material + custo_total_usinagem + custo_total_tratamentos
    lucro_calculado = bruto_lucro = custo_bruto_total * (porcentagem_lucro / 100)
    preco_venda_lote = custo_bruto_total + lucro_calculado
    preco_unitario_final = preco_venda_lote / lote if lote > 0 else 0

    st.markdown("### 📋 Resumo Financeiro da Proposta")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo Direto Total", f"R$ {custo_bruto_total:.2f}")
    c2.metric("Margem aplicada", f"{porcentagem_lucro}% (+R$ {lucro_calculado:.2f})")
    c3.metric("Preço TOTAL do Lote", f"R$ {preco_venda_lote:.2f}")
    c4.metric("Preço UNITÁRIO da Peça", f"R$ {preco_unitario_final:.2f}", delta="Pronto p/ Enviar")

    # --- BOTÃO SALVAR HISTÓRICO COM MULTIVERSÕES ---
    if st.button("💾 Finalizar e Gravar no Histórico", type="primary"):
        novo_registro = {
            "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Código da Peça": codigo_peca if codigo_peca else "N/A",
            "Nome da Peça": nome_peca if nome_peca else "N/A",
            "Empresa": empresa if empresa else "N/A",
            "Comprador": comprador if comprador else "N/A",
            "Lote": lote,
            "Comprimento (mm)": comprimento,
            "Tipo MP": tipo_mp,
            "Detalhes Material": detalhes_material,
            "Custo Material (R$)": round(custo_total_material, 2),
            "Custo Usinagem (R$)": round(custo_total_usinagem, 2),
            "Custo Tratamento (R$)": round(custo_total_tratamentos, 2),
            "Margem Lucro (%)": porcentagem_lucro,
            "Preço Total Lote (R$)": round(preco_venda_lote, 2),
            "Preço Unitário (R$)": round(preco_unitario_final, 2)
        }
        
        df_novo = pd.DataFrame([novo_registro])
        
        if os.path.exists(ARQUIVO_HISTORICO):
            df_hist = pd.read_csv(ARQUIVO_HISTORICO)
            df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
        else:
            df_hist = df_novo
            
        df_hist.to_csv(ARQUIVO_HISTORICO, index=False)
        st.success(f"✅ Sucesso! O orçamento do código '{codigo_peca}' foi adicionado como uma nova linha histórica.")
        
        # Limpa o estado para permitir novas consultas limpas
        st.session_state.dados_carregados = None

# -----------------------------------------------------------------------------
# 3. ABA DO HISTÓRICO GERAL DE CONSULTAS
# -----------------------------------------------------------------------------
with aba_historico:
    st.subheader("📜 Histórico Permanente de Orçamentos Gerados")
    st.write("Abaixo estão listadas todas as consultas e versões geradas. Você pode pesquisar pelo código da peça no topo da tabela.")
    
    if os.path.exists(ARQUIVO_HISTORICO):
        df_visualizar = pd.read_csv(ARQUIVO_HISTORICO)
        # Exibe em ordem decrescente para ver os mais recentes no topo
        st.dataframe(df_visualizar.iloc[::-1], use_container_width=True)
        
        csv_download = df_visualizar.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar Todo o Histórico para o Excel (CSV)", data=csv_download, file_name="historico_geral_usinagem.csv", mime="text/csv")
    else:
        st.info("Nenhuma cotação foi salva no sistema ainda.")
