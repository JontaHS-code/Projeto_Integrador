# ---------------------------
# IMPORTS
# ---------------------------
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
from flask_cors import CORS
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import copy


# ---------------------------
# CARREGA VARIÁVEIS DE AMBIENTE
# ---------------------------
load_dotenv()

# ---------------------------
# CONFIGURAÇÃO DO FLASK
# ---------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------
# CHAVE DA API GEMINI
# ---------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------------------
# CONEXÃO COM O POSTGRESQL DO RENDER
# ---------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
url = urlparse(DATABASE_URL)

try:
    conn = psycopg2.connect(
        dbname=url.path[1:],          # remove a barra inicial
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        cursor_factory=RealDictCursor
    )
    print("Conexão com o banco realizada com sucesso!")
except Exception as e:
    print("Erro de conexão com o banco:", e)

# Configurar a API do Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")

# Função para conexão com o banco
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Erro de conexão com o banco: {e}")
        return None

def get_imagens_pet(pet_id):
    """Busca TODAS as imagens de um pet específico"""
    conn = get_db_connection()
    if conn is None:
        return []
        
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
        SELECT id, url_imagem, descricao_imagem, is_principal, ordem
        FROM imagens_pets 
        WHERE pet_id = %s
        ORDER BY is_principal DESC, ordem ASC, id ASC
        """
        
        cur.execute(query, (pet_id,))
        imagens = cur.fetchall()
        
        # Converter para lista comum
        imagens_list = []
        for img in imagens:
            img_dict = {
                'id': img['id'],
                'url_imagem': img['url_imagem'],
                'descricao_imagem': img['descricao_imagem'],
                'is_principal': img['is_principal'],
                'ordem': img['ordem']
            }
            imagens_list.append(img_dict)
        
        return imagens_list
        
    except Exception as e:
        print(f"Erro ao buscar imagens do pet {pet_id}: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def get_all_pets_disponiveis():
    """Busca todos os pets disponíveis no banco"""
    conn = get_db_connection()
    if conn is None:
        return []
        
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
        SELECT 
            p.id,
            p.nome,
            p.idade_meses,
            p.peso_kg,
            p.sexo,
            p.cor,
            p.personalidade,
            p.cuidados_especiais,
            p.custo_mensal_estimado,
            p.nivel_afetividade,
            p.nivel_brincadeira,
            p.adaptabilidade,
            p.descricao,
            p.disponivel,
            r.nome as raca_nome, 
            r.tamanho as tamanho_raca,
            r.nivel_energia as nivel_energia_raca,
            e.nome as especie_nome,
            cp.orcamento_ideal, 
            cp.tempo_diario_minimo, 
            cp.espaco_necessario,
            cp.estilo_vida_compativel, 
            cp.bom_com_criancas, 
            cp.bom_com_outros_pets,
            cp.experiencia_dono,
            cp.necessita_quintal
        FROM pets p
        JOIN racas r ON p.raca_id = r.id
        JOIN especies e ON r.especie_id = e.id
        LEFT JOIN caracteristicas_pets cp ON p.id = cp.pet_id
        WHERE p.disponivel = true
        ORDER BY p.id
        """
        
        cur.execute(query)
        pets = cur.fetchall()
        
        # Converter para lista de dicionários e buscar imagens
        pets_completos = []
        for pet in pets:
            pet_dict = {}
            for key, value in pet.items():
                pet_dict[key] = value
            
            # Buscar imagens específicas para este pet
            pet_dict['imagens'] = get_imagens_pet(pet_dict['id'])
            pets_completos.append(pet_dict)
        
        return pets_completos
        
    except Exception as e:
        print(f"Erro ao buscar pets: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def calcular_compatibilidade(pet, user_responses):
    """Calcula a compatibilidade do pet com as respostas do usuário (0-100)"""
    print(f"DEBUG: Calculando compatibilidade para {pet['nome']}")
    print(f"DEBUG: User budget: {user_responses.get('budget')}")
    print(f"DEBUG: Pet cost: {pet.get('custo_mensal_estimado')}")
    
    score = 0
    max_score = 0
    
    # Compatibilidade com orçamento (30 pontos)
    budget_map = {
        "Até R$ 100 (básico - ração econômica, cuidados mínimos)": 100,
        "R$ 100-300 (padrão - ração de qualidade, vacinas, alguns acessórios)": 300,
        "R$ 300-600 (premium - ração premium, veterinário particular, pet shop)": 600,
        "Acima de R$ 600 (alto - tudo do melhor, possibilidade de tratamentos especiais)": 1000
    }
    
    user_budget = budget_map.get(user_responses.get('budget'), 300)
    pet_cost = pet.get('custo_mensal_estimado', 0)
    
    if pet_cost <= user_budget:
        score += 30
    elif pet_cost <= user_budget * 1.2:
        score += 20
    elif pet_cost <= user_budget * 1.5:
        score += 10
    
    max_score += 30
    
    # Compatibilidade com tamanho (20 pontos)
    if user_responses.get('size') != 'Não tenho preferência':
        size_map = {
            'Pequeno (até 10kg)': 'Pequeno',
            'Médio (10-25kg)': 'Médio', 
            'Grande (25-45kg)': 'Grande',
            'Muito grande (acima de 45kg)': 'Muito Grande'
        }
        user_size = size_map.get(user_responses.get('size'))
        pet_size = pet.get('tamanho_raca')
        
        if user_size == pet_size:
            score += 20
        elif (user_size == 'Pequeno' and pet_size in ['Pequeno', 'Médio']) or \
             (user_size == 'Médio' and pet_size in ['Pequeno', 'Médio', 'Grande']) or \
             (user_size == 'Grande' and pet_size in ['Médio', 'Grande', 'Muito Grande']):
            score += 15
        else:
            score += 5
        max_score += 20
    
    # Compatibilidade com ambiente (20 pontos)
    environment = user_responses.get('environment', '')
    bom_com_criancas = pet.get('bom_com_criancas', True)
    bom_com_outros_pets = pet.get('bom_com_outros_pets', True)
    
    if 'Sim, tenho crianças pequenas' in environment and bom_com_criancas:
        score += 10
    if 'Sim, tenho outros pets' in environment and bom_com_outros_pets:
        score += 10
    max_score += 20
    
    # Compatibilidade com estilo de vida (15 pontos)
    lifestyle = user_responses.get('lifestyle', '')
    pet_energy = pet.get('nivel_energia_raca', 3)
    
    if lifestyle == 'Sedentário (passo muito tempo em casa)' and pet_energy <= 2:
        score += 15
    elif lifestyle == 'Ativo (gosto de caminhadas e atividades ao ar livre)' and 2 <= pet_energy <= 4:
        score += 15
    elif lifestyle == 'Muito ativo (pratico esportes regularmente)' and pet_energy >= 4:
        score += 15
    elif lifestyle == 'Variável (alguns dias tranquilos, outros agitados)' and 2 <= pet_energy <= 4:
        score += 12
    else:
        score += 8
    max_score += 15
    
    # Compatibilidade com tempo disponível (15 pontos)
    time_map = {
        'Menos de 1 hora (muito pouco tempo)': 1,
        '1-2 horas (tempo limitado)': 2,
        '2-4 horas (tempo razoável)': 3,
        'Mais de 4 horas (muito tempo disponível)': 4
    }
    user_time = time_map.get(user_responses.get('time'), 2)
    pet_time_needed = pet.get('tempo_diario_minimo', 60) / 60
    
    if user_time >= pet_time_needed:
        score += 15
    elif user_time >= pet_time_needed * 0.7:
        score += 10
    else:
        score += 5
    max_score += 15
    
    final_score = min(100, int((score / max_score) * 100))
    print(f"DEBUG: Compatibilidade final para {pet['nome']}: {final_score}%")
    return final_score

def get_pets_por_filtro(filtro=None, especie=None, sexo=None, recomendar=True, user_responses=None):
    """Busca pets com filtros específicos"""
    all_pets = get_all_pets_disponiveis()
    
    if not all_pets:
        return []
    
    pets_filtrados = all_pets
    
    # Aplicar filtros
    if especie:
        pets_filtrados = [pet for pet in pets_filtrados if pet.get('especie_nome', '').lower() == especie.lower()]
    
    if sexo:
        sexo_map = {'macho': 'M', 'fêmea': 'F', 'femea': 'F', 'masculino': 'M', 'feminino': 'F'}
        sexo_filtro = sexo_map.get(sexo.lower(), sexo.upper())
        pets_filtrados = [pet for pet in pets_filtrados if pet.get('sexo', '').upper() == sexo_filtro]
    
    # Calcular compatibilidade se for recomendação
    if recomendar and user_responses:
        for pet in pets_filtrados:
            pet['compatibilidade'] = calcular_compatibilidade(pet, user_responses)
        pets_filtrados.sort(key=lambda x: x.get('compatibilidade', 0), reverse=True)
    
    return pets_filtrados

def get_recommended_pets(user_responses, limit=5):
    """Busca pets compatíveis com base nas respostas do usuário"""
    pets = get_all_pets_disponiveis()
    
    if not pets:
        return []
    
    # Calcular compatibilidade para cada pet
    pets_com_compatibilidade = []
    for pet in pets:
        pet_copy = copy.deepcopy(pet)
        compatibilidade = calcular_compatibilidade(pet_copy, user_responses)
        pet_copy['compatibilidade'] = compatibilidade
        pets_com_compatibilidade.append(pet_copy)
    
    # Ordenar por compatibilidade e pegar os top
    pets_com_compatibilidade.sort(key=lambda x: x['compatibilidade'], reverse=True)
    return pets_com_compatibilidade[:limit]

def formatar_recomendacao_pet(pet, incluir_imagem=True, mostrar_todas_imagens=False):
    """Formata os dados do pet de forma organizada e funcional"""
    
    # Buscar imagens corretamente
    imagens = pet.get('imagens', [])
    print(f"DEBUG: Imagens para {pet['nome']}: {len(imagens)}")
    
    imagem_principal = None
    outras_imagens = []
    
    if imagens:
        # Procurar imagem principal
        for img in imagens:
            if img.get('is_principal'):
                imagem_principal = img
            else:
                outras_imagens.append(img)
        
        # Se não encontrou principal, pega a primeira como principal
        if not imagem_principal and imagens:
            imagem_principal = imagens[0]
            outras_imagens = imagens[1:]
    
    # HTML da imagem - CORRIGIDO
    imagem_html = ""
    if incluir_imagem:
        if imagem_principal and imagem_principal.get('url_imagem'):
            imagem_url = imagem_principal['url_imagem']
            print(f"DEBUG: URL da imagem principal: {imagem_url}")
            imagem_html = f'''
            <div class="pet-image-column">
                <div class="pet-image-container">
                    <img src="{imagem_url}" alt="{pet['nome']}" class="pet-main-image">
                </div>
            </div>
            '''
        else:
            # Placeholder se não tiver imagem
            imagem_html = f'''
            <div class="pet-image-column">
                <div class="pet-image-container">
                    <div class="pet-image-placeholder">
                        <span>🐾</span>
                        <p>{pet['nome']}</p>
                    </div>
                </div>
            </div>
            '''
    
    # Informações básicas
    info_basicas = f'''
    <div class="pet-basic-info-grid">
        <div class="info-item">
            <span class="info-label">Idade</span>
            <span class="info-value">{pet.get('idade_meses', 'N/A')} meses</span>
        </div>
        <div class="info-item">
            <span class="info-label">Peso</span>
            <span class="info-value">{pet.get('peso_kg', 'N/A')} kg</span>
        </div>
        <div class="info-item">
            <span class="info-label">Sexo</span>
            <span class="info-value">{'Macho' if pet.get('sexo') == 'M' else 'Fêmea'}</span>
        </div>
        <div class="info-item">
            <span class="info-label">Cor</span>
            <span class="info-value">{pet.get('cor', 'N/A')}</span>
        </div>
    </div>
    '''
    
    # Características principais
    caracteristicas = f'''
    <div class="pet-features-grid">
        <div class="feature-card">
            <span class="feature-icon">❤️</span>
            <span class="feature-label">Afetividade</span>
            <span class="feature-value">{pet.get('nivel_afetividade', 'N/A')}/5</span>
        </div>
        <div class="feature-card">
            <span class="feature-icon">🎾</span>
            <span class="feature-label">Brincadeira</span>
            <span class="feature-value">{pet.get('nivel_brincadeira', 'N/A')}/5</span>
        </div>
        <div class="feature-card">
            <span class="feature-icon">🏠</span>
            <span class="feature-label">Adaptabilidade</span>
            <span class="feature-value">{pet.get('adaptabilidade', 'N/A')}/5</span>
        </div>
    </div>
    '''
    
    # Informações detalhadas
    info_detalhada = ""
    
    if pet.get('personalidade') and pet.get('personalidade') != 'N/A':
        info_detalhada += f'''
        <div class="detail-card">
            <h4>🎭 Personalidade</h4>
            <p>{pet.get('personalidade')}</p>
        </div>
        '''
    
    if pet.get('cuidados_especiais') and pet.get('cuidados_especiais') != 'N/A':
        info_detalhada += f'''
        <div class="detail-card">
            <h4>💊 Cuidados</h4>
            <p>{pet.get('cuidados_especiais')}</p>
        </div>
        '''
    
    if pet.get('custo_mensal_estimado'):
        info_detalhada += f'''
        <div class="detail-card">
            <h4>💰 Custo Mensal</h4>
            <p>R$ {pet.get('custo_mensal_estimado')}</p>
        </div>
        '''
    
    # Fotos adicionais
    info_fotos = ""
    if outras_imagens and not mostrar_todas_imagens:
        info_fotos = f'''
        <div class="photos-notice">
            <p>📷 Tem {len(outras_imagens)} foto(s) adicional(is) do {pet['nome']}</p>
        </div>
        '''
    
    # Botão de adoção
    botao_adotar = f'''
    <div class="adoption-action">
        <button class="adopt-btn" data-pet-id="{pet['id']}" data-pet-name="{pet['nome']}">
            <span>❤️</span>
            Adotar {pet['nome']}
        </button>
    </div>
    '''
    
    # Layout final ORGANIZADO
    recomendacao = f'''
    <div class="pet-recommendation-card">
        <div class="pet-card-header">
            <div class="pet-title">
                <h3>{pet['nome']}</h3>
                <p class="pet-breed">{pet['raca_nome']} - {pet['especie_nome']}</p>
            </div>
            <div class="compatibility-badge">{pet.get('compatibilidade', 0)}% compatível</div>
        </div>
        
        <div class="pet-card-content">
            {imagem_html}
            
            <div class="pet-info-column">
                {info_basicas}
                {caracteristicas}
                
                <div class="info-details-section">
                    {info_detalhada}
                </div>
                
                {info_fotos}
                {botao_adotar}
            </div>
        </div>
    </div>
    '''
    
    return recomendacao

def processar_pergunta_especifica(pet, pergunta, user_responses, all_pets):
    """Processa perguntas específicas sobre um pet usando Gemini com contexto completo"""
    try:
        # Preparar contexto detalhado
        pets_context = "\n".join([
            f"- {p['nome']}: {p['especie_nome']} {p['raca_nome']}, {p['idade_meses']} meses, R$ {p['custo_mensal_estimado']}/mês, {p.get('compatibilidade', 0)}% compatibilidade"
            for p in all_pets
        ])
        
        contexto = f"""
INFORMAÇÕES REAIS DO BANCO DE DADOS - PET {pet['nome'].upper()}:

DADOS EXATOS DO PET:
- Nome: {pet['nome']}
- Espécie: {pet['especie_nome']}
- Raça: {pet['raca_nome']}
- Idade: {pet['idade_meses']} meses
- Peso: {pet['peso_kg']}kg
- Sexo: {'Macho' if pet['sexo'] == 'M' else 'Fêmea'}
- Cor: {pet['cor']}
- Custo mensal EXATO: R$ {pet['custo_mensal_estimado']}
- Personalidade: {pet['personalidade']}
- Cuidados especiais: {pet['cuidados_especiais']}
- Descrição: {pet['descricao']}
- Nível afetividade: {pet['nivel_afetividade']}/5
- Nível brincadeira: {pet['nivel_brincadeira']}/5
- Adaptabilidade: {pet['adaptabilidade']}/5

COMPATIBILIDADE CALCULADA: {pet.get('compatibilidade', 0)}% (VALOR REAL DO CÁLCULO)

PERFIL DO USUÁRIO:
- Orçamento: {user_responses.get('budget', 'N/A')}
- Tempo disponível: {user_responses.get('time', 'N/A')}
- Estilo de vida: {user_responses.get('lifestyle', 'N/A')}
- Ambiente: {user_responses.get('environment', 'N/A')}

OUTROS PETS DISPONÍVEIS:
{pets_context}

PERGUNTA DO USUÁRIO: "{pergunta}"

INSTRUÇÕES CRÍTICAS:
1. USE os dados REAIS acima como BASE PRINCIPAL
2. NUNCA altere a compatibilidade - use {pet.get('compatibilidade', 0)}% (valor calculado)
3. Para custos, use R$ {pet['custo_mensal_estimado']} (valor real do banco)
4. Complemente com conhecimentos gerais sobre a raça/espécie
5. Seja PRECISO e ÚTIL
6. Mantenha a consistência com os dados do banco
7. Destaque a compatibilidade real quando relevante

Responda de forma natural, conversacional e focada em ajudar o usuário.
"""

        response = model.generate_content(contexto)
        return response.text
        
    except Exception as e:
        print(f"Erro ao processar pergunta específica: {e}")
        return f"Com base nas informações reais do {pet['nome']} no nosso banco: {pet['descricao']}. Custo mensal: R$ {pet['custo_mensal_estimado']}. Compatibilidade com seu perfil: {pet.get('compatibilidade', 0)}%."

chat_sessions = {}

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_responses():
    try:
        data = request.json
        user_responses = data.get('responses')
        session_id = data.get('session_id')

        if not user_responses:
            return jsonify({"error": "Respostas são obrigatórias"}), 400

        # Busca pets compatíveis do banco de dados
        recommended_pets = get_recommended_pets(user_responses)
        
        if not recommended_pets:
            return jsonify({
                "reply": "Não encontrei pets compatíveis com seu perfil no momento. Tente ajustar algumas preferências!"
            })

        # Formatar resposta moderna com os pets recomendados
        resposta = f'''
        <div class="recommendations-container">
            <div class="recommendations-header">
                <h2 class="recommendations-title">Pets Recomendados</h2>
                <p class="recommendations-subtitle">Encontrados com base no seu perfil</p>
            </div>
            
            <div class="pets-grid">
        '''

        for pet in recommended_pets:
            resposta += formatar_recomendacao_pet(pet, incluir_imagem=True)

        resposta += '''
            </div>
            
            <div class="chat-actions">
                <h3 class="actions-title">Próximos Passos</h3>
                <ul class="actions-list">
                    <li class="action-item"><p class="action-text">Pergunte sobre qualquer pet</p></li>
                    <li class="action-item"><p class="action-text">Peça mais opções</p></li>
                    <li class="action-item"><p class="action-text">Solicite mais fotos</p></li>
                    <li class="action-item"><p class="action-text">Clique em Adotar</p></li>
                </ul>
            </div>
        </div>
        '''

        # Armazena os pets recomendados e respostas do usuário na sessão
        chat_sessions[session_id] = {
            'chat': model.start_chat(history=[]),
            'recommended_pets': recommended_pets,
            'user_responses': user_responses,
            'all_pets': get_all_pets_disponiveis()
        }

        return jsonify({
            "reply": resposta,
            "session_id": session_id,
            "pets_recomendados": [pet['nome'] for pet in recommended_pets]
        })

    except Exception as e:
        print(f"Erro na análise: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        session_id = data.get('session_id')
        previous_responses = data.get('previous_responses', {}) 

        if not user_message:
            return jsonify({"error": "Mensagem é obrigatória"}), 400

        if session_id not in chat_sessions:
            return jsonify({
                "reply": "Por favor, complete o questionário primeiro para receber recomendações.",
                "session_id": session_id
            })

        session_data = chat_sessions[session_id]
        chat_obj = session_data['chat']
        recommended_pets = session_data['recommended_pets']
        user_responses = session_data.get('user_responses', {})
        all_pets = session_data.get('all_pets', [])

        user_message_lower = user_message.lower()
        print(f"DEBUG: Mensagem recebida: '{user_message}'")

        # 1. PRIMEIRO: Verificar se é pedido de MAIS FOTOS de um pet específico
        foto_keywords = ['foto', 'fotos', 'fotografia', 'imagem', 'imagens', 'fotinho', 'fotinha', 'outra foto', 'mais foto']
        pet_keywords = [pet['nome'].lower() for pet in all_pets]
        
        is_foto_request = any(keyword in user_message_lower for keyword in foto_keywords)
        has_pet_name = any(pet_name in user_message_lower for pet_name in pet_keywords)
        
        if is_foto_request and has_pet_name:
            print(f"DEBUG: Detectado pedido de FOTOS com nome de pet")
            # Identificar qual pet o usuário quer ver mais fotos
            pet_nome = None
            for pet in all_pets:
                if pet['nome'].lower() in user_message_lower:
                    pet_nome = pet['nome']
                    break
            
            if pet_nome:
                print(f"DEBUG: Buscando mais fotos do pet: {pet_nome}")
                
                # Encontrar o pet específico
                pet_especifico = None
                for pet in all_pets:
                    if pet['nome'].lower() == pet_nome.lower():
                        pet_especifico = pet
                        break
                
                if pet_especifico:
                    imagens = pet_especifico.get('imagens', [])
                    print(f"DEBUG: Pet {pet_nome} tem {len(imagens)} imagens")
                    
                    # Se tiver apenas uma imagem
                    if len(imagens) <= 1:
                        return jsonify({
                            "reply": f"📷 No momento temos apenas uma foto do {pet_nome} no nosso banco.",
                            "session_id": session_id
                        })
                    
                    # Mostrar TODAS as imagens (incluindo a primeira)
                    resposta = f"📸 **Aqui estão todas as fotos do {pet_nome}:**\n\n"
                    
                    # Adicionar informações básicas do pet
                    resposta += f"**{pet_especifico['nome']}** ({pet_especifico['raca_nome']} - {pet_especifico['especie_nome']})\n\n"
                    
                    # Mostrar todas as imagens
                    for i, img in enumerate(imagens, 1):
                        descricao = img.get('descricao_imagem', f'Foto {i} do {pet_especifico["nome"]}')
                        resposta += f"**{descricao}:**\n"
                        resposta += f'<div style="text-align: left; margin: 10px 0;"><img src="{img["url_imagem"]}" alt="{pet_especifico["nome"]}" style="max-width: 200px; max-height: 150px; border-radius: 10px; border: 2px solid #8ecbbb;"></div>\n\n'
                    
                    # Botão Adotar
                    botao_adotar = f'''
<div style="text-align: center; margin-top: 15px;">
    <button class="adopt-button" data-pet-id="{pet_especifico['id']}" data-pet-name="{pet_especifico['nome']}" style="background-color: #5a9b8a; color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.42 4.58a5.4 5.4 0 0 0-7.65 0l-.77.78-.77-.78a5.4 5.4 0 0 0-7.65 0C1.46 6.7 1.33 10.28 4 13l8 8 8-8c2.67-2.72 2.54-6.3.42-8.42z"></path>
        </svg>
        Adotar {pet_especifico['nome']}
    </button>
</div>
'''
                    resposta += botao_adotar
                    
                    print(f"DEBUG: Retornando {len(imagens)} fotos do {pet_nome}")
                    return jsonify({
                        "reply": resposta,
                        "session_id": session_id
                    })
                else:
                    return jsonify({
                        "reply": f"❌ Não encontrei o pet '{pet_nome}' no nosso banco. Os pets disponíveis são: {', '.join([p['nome'] for p in all_pets])}",
                        "session_id": session_id
                    })
            else:
                # Listar pets que têm fotos adicionais
                pets_com_fotos_adicionais = [pet['nome'] for pet in all_pets if len(pet.get('imagens', [])) > 1]
                if pets_com_fotos_adicionais:
                    pets_list = ", ".join(pets_com_fotos_adicionais)
                    return jsonify({
                        "reply": f"📷 De qual pet você gostaria de ver mais fotos? Temos fotos adicionais de: {pets_list}. Digite 'mais fotos do [nome do pet]'.",
                        "session_id": session_id
                    })
                else:
                    return jsonify({
                        "reply": "📷 No momento temos apenas uma foto de cada pet no nosso banco.",
                        "session_id": session_id
                    })

        # 2. SEGUNDO: Perguntas específicas sobre pets individuais
        pet_especifico = None
        for pet in all_pets:
            if pet['nome'].lower() in user_message_lower:
                pet_especifico = pet
                break
        
        if pet_especifico:
            print(f"DEBUG: Pergunta específica sobre {pet_especifico['nome']}")
            
            # Se for uma pergunta sobre compatibilidade ou informações gerais
            if any(term in user_message_lower for term in ['compatibilidade', 'compativel', 'porcentagem', '%']):
                compatibilidade = pet_especifico.get('compatibilidade', 0)
                resposta = f"🎯 **Sobre a compatibilidade do {pet_especifico['nome']}:**\n\n"
                resposta += f"**{pet_especifico['nome']} tem {compatibilidade}% de compatibilidade com seu perfil!**\n\n"
                
                if compatibilidade >= 80:
                    resposta += "🌟 **Excelente compatibilidade!** Este pet atende muito bem às suas preferências.\n\n"
                elif compatibilidade >= 60:
                    resposta += "✅ **Boa compatibilidade!** Este pet atende bem à maioria das suas preferências.\n\n"
                elif compatibilidade >= 40:
                    resposta += "⚠️ **Compatibilidade moderada.** Alguns aspectos podem precisar de adaptação.\n\n"
                else:
                    resposta += "💡 **Compatibilidade baixa.** Talvez outros pets sejam mais adequados.\n\n"
                
                resposta += formatar_recomendacao_pet(pet_especifico, incluir_imagem=True, mostrar_todas_imagens=False)
                return jsonify({"reply": resposta, "session_id": session_id})
            
            # Para outras perguntas específicas, usar Gemini com contexto
            resposta_especifica = processar_pergunta_especifica(pet_especifico, user_message, user_responses, all_pets)
            
            # Adicionar informações básicas e botão de adoção
            resposta = f"🐾 **Sobre o {pet_especifico['nome']}:**\n\n"
            resposta += resposta_especifica + "\n\n"
            resposta += formatar_recomendacao_pet(pet_especifico, incluir_imagem=True, mostrar_todas_imagens=False)
            
            return jsonify({"reply": resposta, "session_id": session_id})

        # 3. TERCEIRO: Consultas sobre quantidade e tipos
        if any(term in user_message_lower for term in ['quantos', 'quantas', 'total', 'tem quantos']):
            print(f"DEBUG: Detectado pedido de QUANTIDADE")
            # Contar por tipo
            cachorros = [pet for pet in all_pets if 'cachorro' in pet.get('especie_nome', '').lower()]
            gatos = [pet for pet in all_pets if 'gato' in pet.get('especie_nome', '').lower()]
            coelhos = [pet for pet in all_pets if 'coelho' in pet.get('especie_nome', '').lower()]
            
            # Verificar se pergunta sobre fêmeas/machos
            if any(term in user_message_lower for term in ['fêmea', 'femea', 'feminino', 'cachorra', 'gata']):
                femeas = [pet for pet in all_pets if pet.get('sexo') == 'F']
                cachorras = [pet for pet in cachorros if pet.get('sexo') == 'F']
                gatas = [pet for pet in gatos if pet.get('sexo') == 'F']
                
                if 'cachorr' in user_message_lower:
                    resposta = f"🐕 **Temos {len(cachorras)} cachorra(s) disponível(is):** {', '.join([p['nome'] for p in cachorras]) if cachorras else 'Nenhuma no momento'}"
                elif 'gat' in user_message_lower:
                    resposta = f"🐈 **Temos {len(gatas)} gata(s) disponível(is):** {', '.join([p['nome'] for p in gatas]) if gatas else 'Nenhuma no momento'}"
                else:
                    resposta = f"👩 **Temos {len(femeas)} fêmeas disponíveis no total**"
                    
                return jsonify({"reply": resposta, "session_id": session_id})
            
            # Consultas gerais
            if 'cachorr' in user_message_lower:
                resposta = f"🐕 **Temos {len(cachorros)} cachorro(s) disponível(is) no total:** {', '.join([p['nome'] for p in cachorros])}"
            elif 'gat' in user_message_lower:
                resposta = f"🐈 **Temos {len(gatos)} gato(s) disponível(is) no total:** {', '.join([p['nome'] for p in gatos])}"
            elif 'coelh' in user_message_lower:
                resposta = f"🐇 **Temos {len(coelhos)} coelho(s) disponível(is) no total:** {', '.join([p['nome'] for p in coelhos])}"
            else:
                resposta = f"🐾 **No momento temos {len(all_pets)} pets disponíveis para adoção!**\n\n"
                resposta += f"**Distribuição:**\n"
                resposta += f"- 🐕 Cachorros: {len(cachorros)}\n"
                resposta += f"- 🐈 Gatos: {len(gatos)}\n"
                resposta += f"- 🐇 Coelhos: {len(coelhos)}\n\n"
                resposta += "Quer ver pets de algum tipo específico? É só perguntar!"
            
            return jsonify({"reply": resposta, "session_id": session_id})

        # 4. QUARTO: Pedido para ver mais opções ou tipos específicos
        if any(term in user_message_lower for term in ['mais opções', 'outras opções', 'outros pets', 'ver todos', 'mostrar todos', 'todos os']):
            print(f"DEBUG: Detectado pedido de MAIS OPÇÕES")
            # Verificar se é um tipo específico
            if 'cachorr' in user_message_lower:
                pets_tipo = [pet for pet in all_pets if 'cachorro' in pet.get('especie_nome', '').lower()]
                tipo_nome = "cachorros"
            elif 'gat' in user_message_lower:
                pets_tipo = [pet for pet in all_pets if 'gato' in pet.get('especie_nome', '').lower()]
                tipo_nome = "gatos"
            elif 'coelh' in user_message_lower:
                pets_tipo = [pet for pet in all_pets if 'coelho' in pet.get('especie_nome', '').lower()]
                tipo_nome = "coelhos"
            else:
                pets_tipo = all_pets
                tipo_nome = "pets"
            
            if not pets_tipo:
                return jsonify({"reply": f"❌ Não temos {tipo_nome} disponíveis no momento.", "session_id": session_id})
            
            resposta = f"🐾 **Aqui estão todos os {tipo_nome} disponíveis:**\n\n"
            for i, pet in enumerate(pets_tipo, 1):
                # Calcular compatibilidade se não tiver
                if 'compatibilidade' not in pet:
                    pet['compatibilidade'] = calcular_compatibilidade(pet, user_responses)
                
                resposta += f"### {i}. {pet['nome']} - {pet.get('compatibilidade', 0)}%\n"
                resposta += formatar_recomendacao_pet(pet, incluir_imagem=True, mostrar_todas_imagens=False)
            
            return jsonify({"reply": resposta, "session_id": session_id})

        # 5. QUINTO: Pedido de recomendações específicas
        if any(term in user_message_lower for term in ['recomende', 'sugira', 'mostre', 'ver', 'quero ver']):
            print(f"DEBUG: Detectado pedido de RECOMENDAÇÃO")
            # Detectar filtros
            especie = None
            sexo = None
            
            if 'cachorr' in user_message_lower:
                especie = 'cachorro'
            elif 'gat' in user_message_lower:
                especie = 'gato'
            elif 'coelh' in user_message_lower:
                especie = 'coelho'
            
            if any(term in user_message_lower for term in ['fêmea', 'femea', 'feminino']):
                sexo = 'F'
            elif any(term in user_message_lower for term in ['macho', 'masculino']):
                sexo = 'M'
            
            pets_filtrados = get_pets_por_filtro(especie=especie, sexo=sexo, recomendar=True, user_responses=user_responses)
            
            if not pets_filtrados:
                descricao = []
                if especie: descricao.append(especie)
                if sexo: descricao.append('macho' if sexo == 'M' else 'fêmea')
                filtro_texto = ' '.join(descricao) if descricao else 'com esses filtros'
                return jsonify({"reply": f"❌ Não encontrei pets {filtro_texto} no momento.", "session_id": session_id})
            
            # Ordenar por compatibilidade
            pets_filtrados.sort(key=lambda x: x.get('compatibilidade', 0), reverse=True)
            
            descricao = []
            if especie: descricao.append(especie + 's')
            if sexo: descricao.append('machos' if sexo == 'M' else 'fêmeas')
            filtro_texto = ' '.join(descricao) if descricao else 'recomendados'
            
            resposta = f"🎯 **Aqui estão os {filtro_texto} para você:**\n\n"
            for i, pet in enumerate(pets_filtrados, 1):
                resposta += f"### {i}. {pet['nome']} - {pet.get('compatibilidade', 0)}%\n"
                resposta += formatar_recomendacao_pet(pet, incluir_imagem=True, mostrar_todas_imagens=False)
            
            return jsonify({"reply": resposta, "session_id": session_id})

        # 6. SEXTO: Para outras perguntas, usar o Gemini com contexto completo
        print(f"DEBUG: Usando Gemini para resposta genérica")
        
        # Preparar contexto detalhado
        pets_context = "\n\n".join([
            f"Pet: {pet.get('nome', 'N/A')} | Espécie: {pet.get('especie_nome', 'N/A')} | Raça: {pet.get('raca_nome', 'N/A')} | Sexo: {'Macho' if pet.get('sexo') == 'M' else 'Fêmea'} | Idade: {pet.get('idade_meses', 'N/A')} meses | Custo: R$ {pet.get('custo_mensal_estimado', 'N/A')} | Compatibilidade: {pet.get('compatibilidade', 0)}% | Personalidade: {pet.get('personalidade', 'N/A')}"
            for pet in all_pets
        ])

        context = f"""
INFORMAÇÕES REAIS DO BANCO DE DADOS:
Total de pets disponíveis: {len(all_pets)}
Lista de pets: {[pet['nome'] for pet in all_pets]}

DETALHES COMPLETOS DE TODOS OS PETS:
{pets_context}

PERFIL DO USUÁRIO:
{user_responses}

COMPATIBILIDADES CALCULADAS:
{" | ".join([f"{pet['nome']}: {pet.get('compatibilidade', 0)}%" for pet in all_pets if 'compatibilidade' in pet])}

PERGUNTA DO USUÁRIO: "{user_message}"

INSTRUÇÕES CRÍTICAS:
- USE SEMPRE as informações reais do banco de dados como BASE PRINCIPAL
- NUNCA invente compatibilidades - use apenas os valores calculados ({[f"{pet['nome']}: {pet.get('compatibilidade', 0)}%" for pet in all_pets if pet.get('compatibilidade', 0) > 0]})
- Para custos, use os valores EXATOS do banco (R$ {[f"{pet['nome']}: R$ {pet.get('custo_mensal_estimado', 'N/A')}" for pet in all_pets]})
- Para perguntas sobre pets específicos, refira-se aos dados reais do banco
- Complemente com conhecimentos gerais quando apropriado
- Seja preciso, útil e mantenha a consistência com os dados reais
- Destaque a compatibilidade calculada quando relevante
"""

        response = chat_obj.send_message(context)
        # No final da rota /api/chat, antes do return
        resposta_final = response.text if 'response' in locals() else resposta

        return jsonify({
            "reply": resposta_final,
            "session_id": session_id
        })
        return jsonify({"reply": response.text, "session_id": session_id})

    except Exception as e:
        print(f"Erro no chat: {e}")
        return jsonify({"error": str(e)}), 500

# Rota para processar adoção
@app.route('/api/adotar', methods=['POST'])
def adotar_pet():
    try:
        data = request.json
        pet_id = data.get('pet_id')
        pet_nome = data.get('pet_nome')
        session_id = data.get('session_id')
        nome = data.get('nome')
        email = data.get('email')
        telefone = data.get('telefone')
        whatsapp = data.get('whatsapp')
        endereco = data.get('endereco')
        cidade = data.get('cidade')
        estado = data.get('estado')
        tipo_residencia = data.get('tipo_residencia')
        tem_quintal = data.get('tem_quintal')
        numero_moradores = data.get('numero_moradores')
        tem_criancas = data.get('tem_criancas')
        tem_outros_pets = data.get('tem_outros_pets')
        experiencia = data.get('experiencia')
        rotina_planejada = data.get('rotina_planejada')
        motivacao = data.get('motivacao')
        mensagem = data.get('mensagem')
        
        # Campos obrigatórios atualizados
        campos_obrigatorios = [
            pet_id, pet_nome, nome, email, telefone, endereco, 
            cidade, estado, tipo_residencia, tem_quintal, 
            numero_moradores, experiencia, rotina_planejada, motivacao
        ]
        
        if not all(campos_obrigatorios):
            return jsonify({"error": "Todos os campos obrigatórios devem ser preenchidos"}), 400
        
        # Aqui você pode salvar no banco de dados o interesse na adoção
        print(f"Interesse em adoção registrado:")
        print(f"Pet: {pet_nome} (ID: {pet_id})")
        print(f"Sessão: {session_id}")
        print(f"Dados do adotante: {nome}, {email}, {telefone}, WhatsApp: {whatsapp}")
        print(f"Endereço: {endereco}, {cidade}-{estado}")
        print(f"Residência: {tipo_residencia}, Quintal: {tem_quintal}")
        print(f"Moradores: {numero_moradores}, Crianças: {tem_criancas}, Outros pets: {tem_outros_pets}")
        print(f"Experiência: {experiencia}")
        print(f"Rotina planejada: {rotina_planejada}")
        print(f"Motivação: {motivacao}")
        print(f"Mensagem: {mensagem}")
        
        return jsonify({
            "success": True,
            "message": f"🎉 Ótima escolha! Seu interesse em adotar o {pet_nome} foi registrado!",
            "next_steps": [
                "Nossa equipe entrará em contato em até 24 horas",
                "Prepare os documentos necessários para adoção",
                "Agendaremos uma visita para conhecer o pet",
                "Será realizada uma entrevista para garantir a melhor compatibilidade"
            ]
        })
        
    except Exception as e:
        print(f"Erro no processo de adoção: {e}")
        return jsonify({"error": str(e)}), 500
    
# Rotas para API
@app.route('/api/test-db', methods=['GET'])
def test_db():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Não foi possível conectar ao banco de dados"}), 500
            
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as total FROM pets')
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "Conexão bem-sucedida",
            "total_pets": result[0],
            "database_url": DATABASE_URL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pets', methods=['GET'])
def get_all_pets():
    try:
        pets = get_all_pets_disponiveis()
        return jsonify({
            "pets": pets,
            "count": len(pets)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
