from flask import Flask, request, jsonify, render_template
from google import genai
import os
from dotenv import load_dotenv
from flask_cors import CORS
import random

load_dotenv()
app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

PET_EXPERT_PROMPT = """
Você é o "PetMatch", assistente virtual especializado em ajudar pessoas a encontrar o pet perfeito para elas. Siga estas regras:

1. **Foco Principal**:
   - Responda APENAS sobre os pets que foram recomendados ao usuário
   - Relacione sempre com o perfil e respostas do questionário
   - Seja detalhado, informativo e natural

2. **Quando o assunto for sobre os pets recomendados**:
   - Explique características específicas do pet
   - Dê dicas personalizadas baseadas no perfil
   - Compare com outras opções quando relevante
   - Aborde: cuidados, adaptação, custos, comportamento
   - Use exemplos concretos e linguagem natural

3. **Quando o assunto NÃO for sobre os pets recomendados**:
   - Responda educadamente: "Vamos focar nos pets que recomendei para você!"
   - Sugira: "Posso te contar mais sobre [nomes dos pets recomendados]"

4. **Formato das Respostas**:
   - Linguagem natural e fluida
   - Detalhes relevantes e personalizados
   - Emojis para melhorar a experiência
   - Parágrafos bem estruturados

5. **Exemplo de Boa Resposta**:
   "O Thor (Golden Retriever) que recomendei é perfeito para seu perfil porque... 
   Ele se adapta bem a [detalhe do perfil]. 
   Cuidados importantes: [lista personalizada]. 
   Dica especial: [sugestão específica]."

6. **Restrições**:
   - Nunca sugira novos pets além dos já recomendados
   - Mantenha o foco nas recomendações feitas
   - Seja natural, não robótico
"""

ANALYSIS_PROMPT = """
Com base nestas respostas do usuário:
{user_responses}

Gere 3-5 recomendações de pets detalhadas e personalizadas com:

1. **Nome Criativo**: Invente um nome fictício e carismático
2. **Raça e Tipo**: Especifique se é Cão, Gato ou Outro
3. **Descrição Completa**:
   - Personalidade e características
   - Nível de energia e compatibilidade com o perfil
   - Necessidades específicas

4. **Ambiente Ideal**:
   - Tipo de moradia necessária
   - Espaço requerido
   - Adaptabilidade

5. **Cuidados Específicos**:
   - Lista detalhada de cuidados
   - Frequência de exercícios
   - Necessidades de higiene

6. **Custo Mensal Estimado**:
   - Faixa de valores detalhada
   - Itens incluídos no custo
   - Possíveis gastos extras

7. **Motivo da Recomendação**:
   - Relação clara com as respostas do usuário
   - Pontos fortes para este perfil específico
   - Adaptação ao estilo de vida

8. **Dica Especial**:
   - Conselho personalizado para o usuário
   - Sugestão de adaptação
   - Informação útil específica

Formate cada recomendação como:

**Nome do Pet** (Raça - Tipo)
🌟 Compatibilidade: X/5 (explicação detalhada)
🏠 Ambiente Ideal: [descrição completa]
🐾 Personalidade: [descrição rica e vívida]
💡 Cuidados Necessários: [lista detalhada]
💰 Custo Mensal: [faixa realista] (incluindo [itens])
🔍 Dica Especial: [conselho personalizado]

Seja extremamente detalhado e relacione cada ponto com as respostas do usuário!
"""

chat_sessions = {}

@app.route('/')
def serve_index():
    return render_template('app.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_responses():
    try:
        data = request.json
        user_responses = data.get('responses')
        session_id = data.get('session_id')
        
        if not user_responses:
            return jsonify({"error": "Respostas são obrigatórias"}), 400

        # Formata as respostas para o prompt
        formatted_responses = "\n".join([f"{key}: {value}" for key, value in user_responses.items()])
        full_prompt = ANALYSIS_PROMPT.format(user_responses=formatted_responses)

        # Usa o Gemini para analisar as respostas
        chat = client.chats.create(model="gemini-1.5-flash")
        response = chat.send_message(full_prompt)
        
        # Armazena a sessão para perguntas posteriores
        chat_sessions[session_id] = chat

        return jsonify({
            "reply": response.text,
            "session_id": session_id
        })

    except Exception as e:
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

        chat = chat_sessions[session_id]
        
        # Contexto para respostas mais inteligentes
        context = f"""
        Perfil do usuário:
        {previous_responses}

        Pergunta atual: "{user_message}"

        Instruções para resposta:
        1. Analise se a pergunta é sobre os pets recomendados
        2. Se for, responda de forma:
           - Detalhada e personalizada
           - Com informações úteis e específicas
           - Relacionando com o perfil do usuário
        3. Se NÃO for, responda:
           "Vamos focar nos pets que recomendei para você! Quer saber mais sobre algum deles?"
        4. Seja natural e informativo
        5. Use emojis para melhorar a comunicação
        """
        
        response = chat.send_message(context)

        return jsonify({
            "reply": response.text,
            "session_id": session_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)