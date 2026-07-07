import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuração da página
st.set_page_config(page_title="Gerador de Orçamentos", page_icon="💰", layout="wide")

st.title("🛠️ Sistema Inteligente de Orçamentos")
st.write("Preencha os dados abaixo para calcular o orçamento de usinagem.")

# 1. SIMULAÇÃO DOS DADOS DA SUA ABA "CONSTANTES"
# (Em produção, você pode carregar direto do seu CSV usando pd.read_csv)
DADOS_MATERIAIS = {
    "aço sx": {"constante": 0.68, "preco_kg": 18.0},
    "aço red": {"constante": 0.62, "preco_kg": 15.0},
    "aluminio red": {"constante": 0.212, "preco_kg": 35.0},
    "latao red": {"constante": 0.68, "preco_kg": 45.0}
}

DADOS_MAQUINAS = {
    "Torno Automático": 120.0,
    "CNC": 150.0,
    "Freza": 120.0,
    "Furadeira": 70.0
}

# 2. CRIAÇÃO DAS ABAS NO STREAMLIT (Interface Amigável)
aba_calculo, aba_historico = st.tabs(["📊 Novo Orçamento", "📜 Histórico de Consultas"])

with aba_calculo:
    st.subheader("Dados do Cliente e Produto")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        empresa = st.text_input("Empresa", placeholder="Ex: TS")
        comprador = st.text_input("Comprador", placeholder="Ex: Guilherme")
    with col2:
        nome_peca = st.text_input("Nome da Peça", placeholder="Ex: Ferrolho")
        codigo_peca = st.text_input("Código da Peça", placeholder="Ex: 8-010-11358-00")
    with col3:
        lote = st.number_input("Quantidade do Lote", min_value=1, value=100, step=10)
        comprimento = st.number_input("Comprimento da Peça (mm)", min_value=0.0, value=211.5)

    st.markdown("---")
    st.subheader("Configuração Técnica (Matéria-Prima e Usinagem)")
    col4, col5, col6 = st.columns(3)

    with col4:
        # Usuário leigo apenas escolhe em uma lista, sem risco de digitar errado
        material_selecionado = st.selectbox("Selecione o Material", list(DADOS_MATERIAIS.keys()))
        constante = DADOS_MATERIAIS[material_selecionado]["constante"]
        preco_base_mat = DADOS_MATERIAIS[material_selecionado]["preco_kg"]
        
        st.caption(f"ℹ️ Constante: {constante} | Preço/kg base: R$ {preco_base_mat:.2f}")

    with col5:
        maquina_selecionada = st.selectbox("Máquina Principal", list(DADOS_MAQUINAS.keys()))
        valor_hora_maquina = DADOS_MAQUINAS[maquina_selecionada]
        st.caption(f"ℹ️ Valor/Hora da Máquina: R$ {valor_hora_maquina:.2f}")

    with col6:
        tempo_producao = st.number_input("Produção por Hora (Peças/h)", min_value=1, value=50)

    # 3. LÓGICA DE CÁLCULO (Substitua pelas fórmulas REAIS do seu Excel)
    # Exemplo fictício baseado nos seus prints:
    peso_peca = (comprimento * constante) / 1000 # Cálculo hipotético
    total_quilos = peso_peca * lote
    custo_materia_prima = total_quilos * preco_base_mat
    
    horas_necessarias = lote / tempo_producao
    custo_usinagem = horas_necessarias * valor_hora_maquina
    
    custo_total_bruto = custo_materia_prima + custo_usinagem
    lucro_estimado = custo_total_bruto * 0.30 # 30% de lucro
    valor_com_impostos = (custo_total_bruto + lucro_estimado) * 1.10 # +10% impostos

    st.markdown("---")
    st.subheader("💰 Resultado do Orçamento")
    
    # Exibição em cartões (Metrics) muito visuais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peso Total do Lote", f"{total_quilos:.2f} kg")
    c2.metric("Custo Matéria-Prima", f"R$ {custo_materia_prima:.2f}")
    c3.metric("Custo Usinagem", f"R$ {custo_usinagem:.2f}")
    c4.metric("Preço Final (com Impostos)", f"R$ {valor_com_impostos:.2f}", delta="Calculado")

    # 4. BOTÃO PARA SALVAR NO HISTÓRICO
    if st.button("💾 Salvar Orçamento no Histórico", type="primary"):
        # Criando a linha com os dados atuais
        novo_registro = {
            "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Empresa": empresa,
            "Peça": nome_peca,
            "Lote": lote,
            "Material": material_selecionado,
            "Preço Final": f"R$ {valor_com_impostos:.2f}"
        }
        
        # Cria ou alimenta um arquivo local (Para testes locais funcionar, mas lembre de usar Google Sheets na Nuvem!)
        arquivo_historico = "historico_orcamentos.csv"
        df_novo = pd.DataFrame([novo_registro])
        
        if os.path.exists(arquivo_historico):
            df_hist = pd.read_csv(arquivo_historico)
            df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
        else:
            df_hist = df_novo
            
        df_hist.to_csv(arquivo_historico, index=False)
        st.success("Orçamento salvo com sucesso no histórico!")

# 5. ABA DO HISTÓRICO DE CONSULTAS
with aba_historico:
    st.subheader("Histórico de Orçamentos Gerados")
    arquivo_historico = "historico_orcamentos.csv"
    
    if os.path.exists(arquivo_historico):
        df_visualizar = pd.read_csv(arquivo_historico)
        # Mostra uma tabela interativa que permite buscar, filtrar e ordenar
        st.dataframe(df_visualizar, use_container_width=True)
        
        # Botão para baixar todo o histórico de volta para o Excel se quiserem
        csv_download = df_visualizar.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Histórico em CSV", data=csv_download, file_name="historico_geral.csv", mime="text/csv")
    else:
        st.info("Nenhum orçamento foi salvo ainda.")
