// ========== VARIÁVEIS GLOBAIS ==========
let sessionId =
  localStorage.getItem("petAjudaSessionId") ||
  "sessao-" + Math.random().toString(36).substr(2, 9);

document.addEventListener("DOMContentLoaded", function () {
  const messagesContainer = document.getElementById("messages-container");
  const messageInput = document.getElementById("message-input");
  const sendButton = document.getElementById("send-button");
  const inputContainer = document.getElementById("input-container");
  const restartButton = document.getElementById("restart-button");
  const adoptionModal = document.getElementById("adoption-modal");
  const adoptionForm = document.getElementById("adoption-form");
  let isWaitingForResponse = false;
  let currentQuestionIndex = 0;
  let userResponses = {};
  let hasSentRecommendations = false;

  const questions = [
    {
      question: "Qual é o seu orçamento mensal para cuidados com um pet?",
      options: [
        "Até R$ 100 (básico - ração econômica, cuidados mínimos)",
        "R$ 100-300 (padrão - ração de qualidade, vacinas, alguns acessórios)",
        "R$ 300-600 (premium - ração premium, veterinário particular, pet shop)",
        "Acima de R$ 600 (alto - tudo do melhor, possibilidade de tratamentos especiais)",
      ],
      key: "budget",
    },
    {
      question: "Quanto tempo você pode dedicar diariamente ao seu pet?",
      options: [
        "Menos de 1 hora (muito pouco tempo)",
        "1-2 horas (tempo limitado)",
        "2-4 horas (tempo razoável)",
        "Mais de 4 horas (muito tempo disponível)",
      ],
      key: "time",
    },
    {
      question: "Qual é o seu estilo de vida?",
      options: [
        "Sedentário (passo muito tempo em casa)",
        "Ativo (gosto de caminhadas e atividades ao ar livre)",
        "Muito ativo (pratico esportes regularmente)",
        "Variável (alguns dias tranquilos, outros agitados)",
      ],
      key: "lifestyle",
    },
    {
      question: "Qual é a sua personalidade?",
      options: [
        "Calmo e tranquilo",
        "Brincalhão e energético",
        "Organizado e metódico",
        "Aventureiro e espontâneo",
      ],
      key: "personality",
    },
    {
      question: "Que tipo de relação você busca com seu pet?",
      options: [
        "Companhia tranquila e afetuosa",
        "Um parceiro para atividades e brincadeiras",
        "Um pet independente que não preciso de muita atenção",
        "Um pet que seja quase como um filho, com muita interação",
      ],
      key: "relationship",
    },
    {
      question: "Qual tamanho de pet você prefere?",
      options: [
        "Pequeno (até 10kg)",
        "Médio (10-25kg)",
        "Grande (25-45kg)",
        "Muito grande (acima de 45kg)",
        "Não tenho preferência",
      ],
      key: "size",
    },
    {
      question: "Você tem crianças ou outros pets em casa?",
      options: [
        "Sim, tenho crianças pequenas",
        "Sim, tenho outros pets",
        "Sim, tenho crianças e outros pets",
        "Não, será meu único pet",
      ],
      key: "environment",
    },
  ];

  // Inicia o questionário
  startQuestionnaire();

  function startQuestionnaire() {
    currentQuestionIndex = 0;
    userResponses = {};
    hasSentRecommendations = false;
    messagesContainer.innerHTML = "";
    messageInput.disabled = true;
    sendButton.disabled = true;
    restartButton.style.display = "none";

    setTimeout(() => {
      addMessage(
        "bot",
        "Oi! Eu sou o PetMatch, seu guia para encontrar o pet perfeito para você! 💖\n\nVamos começar com um pequeno questionário para entender seu estilo de vida e preferências."
      );
      setTimeout(() => askQuestion(), 1500);
    }, 1000);
  }

  function askQuestion() {
    if (currentQuestionIndex < questions.length) {
      const question = questions[currentQuestionIndex];
      const questionId = `question-${currentQuestionIndex}`;

      // Desabilita todos os botões de confirmação anteriores
      document.querySelectorAll(".confirm-button").forEach((btn) => {
        btn.disabled = true;
        btn.style.opacity = "0.6";
      });

      let message = `<div class="question-container" id="${questionId}">
                <p>${question.question}</p>
                <div class="options-container">`;

      question.options.forEach((option, index) => {
        message += `<button class="option-button" data-index="${index}">${option}</button>`;
      });

      message += `</div>
                <button class="confirm-button" id="confirm-${currentQuestionIndex}" disabled>Confirmar</button>
            </div>`;

      addMessage("bot", message);

      // Adiciona listeners aos botões de opção
      document
        .querySelectorAll(`#${questionId} .option-button`)
        .forEach((button) => {
          button.addEventListener("click", function () {
            // Remove seleção anterior
            document
              .querySelectorAll(`#${questionId} .option-button`)
              .forEach((btn) => {
                btn.classList.remove("selected");
              });

            // Seleciona o atual
            this.classList.add("selected");

            // Habilita o botão de confirmação
            const confirmBtn = document.getElementById(
              `confirm-${currentQuestionIndex}`
            );
            confirmBtn.disabled = false;
            confirmBtn.style.opacity = "1";
          });
        });

      // Adiciona listener ao botão de confirmação
      document
        .getElementById(`confirm-${currentQuestionIndex}`)
        .addEventListener("click", function () {
          const selectedOption = document.querySelector(
            `#${questionId} .option-button.selected`
          );
          if (selectedOption) {
            // Armazena resposta
            userResponses[question.key] =
              question.options[selectedOption.dataset.index];

            // Mostra a resposta do usuário
            addMessage("user", question.options[selectedOption.dataset.index]);

            // Desabilita esta pergunta
            this.disabled = true;
            this.style.opacity = "0.6";
            document
              .querySelectorAll(`#${questionId} .option-button`)
              .forEach((btn) => {
                btn.disabled = true;
              });

            // Avança para próxima pergunta
            currentQuestionIndex++;
            setTimeout(() => askQuestion(), 500);
          }
        });
    } else {
      submitQuestionnaire();
    }
  }

  function submitQuestionnaire() {
    addMessage(
      "bot",
      "Obrigado pelas respostas! Estou analisando para encontrar os pets perfeitos para você..."
    );

    // Envia as respostas para o backend
    setTimeout(() => {
      analyzeResponses();
    }, 2000);
  }

  async function analyzeResponses() {
    if (hasSentRecommendations) return;
    hasSentRecommendations = true;

    try {
      showTypingIndicator();

      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          responses: userResponses,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();
      removeTypingIndicator();

      // Adiciona classe especial para as recomendações
      const recommendationDiv = document.createElement("div");
      recommendationDiv.className =
        "message bot-message recommendation-highlight";
      recommendationDiv.innerHTML = processBotMessage(data.reply);
      messagesContainer.appendChild(recommendationDiv);

      // Adiciona event listeners aos botões de adoção
      setTimeout(() => {
        attachAdoptionButtonListeners();
      }, 300);

      // Adiciona mensagem de instrução
      addMessage(
        "bot",
        "Agora você pode me perguntar mais detalhes sobre qualquer um dos pets recomendados! 😊"
      );

      // Libera o chat para perguntas
      messageInput.disabled = false;
      sendButton.disabled = true;
      messageInput.focus();

      // Mostra o botão de reiniciar
      restartButton.style.display = "flex";
    } catch (error) {
      removeTypingIndicator();
      addMessage("error", `Erro: ${error.message || "Falha na conexão"}`);
      console.error("Erro na análise:", error);
    }
  }

  // Configura o botão de reiniciar
  restartButton.addEventListener("click", function () {
    startQuestionnaire();
  });

  messageInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";
    sendButton.disabled = this.value.trim() === "" || isWaitingForResponse;
  });

  messageInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !sendButton.disabled) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendButton.addEventListener("click", sendMessage);

  async function sendMessage() {
    const messageText = messageInput.value.trim();
    if (!messageText || isWaitingForResponse) return;

    addMessage("user", messageText);
    messageInput.value = "";
    sendButton.disabled = true;
    showTypingIndicator();
    isWaitingForResponse = true;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageText,
          session_id: sessionId,
          previous_responses: userResponses,
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();
      removeTypingIndicator();

      // Verifica se é sobre as recomendações
      if (
        data.reply.toLowerCase().includes("desculpe") ||
        data.reply.toLowerCase().includes("focar nos pets")
      ) {
        addMessage("bot", data.reply);
      } else {
        // Destaca as respostas sobre recomendações
        const replyDiv = document.createElement("div");
        replyDiv.className = "message bot-message recommendation-highlight";
        replyDiv.innerHTML = processBotMessage(data.reply);
        messagesContainer.appendChild(replyDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Adiciona event listeners aos botões de adoção
        setTimeout(() => {
          attachAdoptionButtonListeners();
        }, 300);
      }
    } catch (error) {
      removeTypingIndicator();
      addMessage("error", `Erro: ${error.message || "Falha na conexão"}`);
      console.error("Erro no chat:", error);
    } finally {
      isWaitingForResponse = false;
      messageInput.focus();
    }
  }

  function addMessage(sender, text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}-message fade-in`;

    if (sender === "bot" || sender === "error") {
      messageDiv.innerHTML = processBotMessage(text);
    } else {
      messageDiv.textContent = text;
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Para mensagens do bot, agenda a verificação de botões
    if (sender === "bot") {
      setTimeout(() => {
        attachAdoptionButtonListeners();
      }, 200);
    }
  }

  // Função para processar mensagens do bot com HTML seguro
  function processBotMessage(text) {
    console.log("DEBUG: Processando mensagem do bot - Tamanho:", text.length);
    console.log("DEBUG: Contém imagem?", text.includes("pet-main-image"));

    // Se contém estrutura de recomendações, processa como HTML
    if (
      text.includes("recommendations-container") ||
      text.includes("pet-card")
    ) {
      console.log("DEBUG: Detectada estrutura de recomendações");
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = formatMessage(text);
      return tempDiv.innerHTML;
    }

    return formatMessage(text);
  }

  function formatMessage(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");
  }

  // Função para anexar event listeners aos botões de adoção
  // Função para anexar event listeners aos botões de adoção - CORRIGIDA
  function attachAdoptionButtonListeners() {
    console.log("Procurando botões de adoção...");

    // Use TODAS as classes possíveis de botões de adoção
    const adoptionButtons = document.querySelectorAll(
      ".adopt-button, .adopt-btn"
    );
    console.log(`Encontrados ${adoptionButtons.length} botões de adoção`);

    adoptionButtons.forEach((button) => {
      // Remove event listener anterior para evitar duplicação
      button.removeEventListener("click", handleAdoptionClick);

      // Adiciona novo listener
      button.addEventListener("click", handleAdoptionClick);
    });
  }

  // Função separada para lidar com clique nos botões de adoção
  function handleAdoptionClick(e) {
    e.preventDefault();
    e.stopPropagation();

    const petId = this.getAttribute("data-pet-id");
    const petName = this.getAttribute("data-pet-name");

    console.log("Botão de adoção clicado:", { petName, petId });

    if (petId && petName) {
      abrirFormularioAdocao(petName, parseInt(petId));
    } else {
      console.error("Dados do pet não encontrados no botão:", this);
    }
  }

  function showTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.id = "typing-indicator";
    indicator.className = "message bot-message typing-indicator";
    indicator.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    messagesContainer.appendChild(indicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function removeTypingIndicator() {
    document.getElementById("typing-indicator")?.remove();
  }

  // Configuração do formulário de adoção
  adoptionForm.addEventListener("submit", handleAdoptionSubmit);
});

// ========== FUNÇÕES GLOBAIS PARA ADOÇÃO ==========

// Função para abrir formulário de adoção
function abrirFormularioAdocao(nomePet, idPet) {
  console.log("Abrindo formulário para:", nomePet, idPet);

  // Buscar informações completas do pet
  buscarInfoPet(idPet)
    .then((petInfo) => {
      // Criar ou atualizar o modal
      criarModalAdocao(petInfo);

      // Mostra o modal
      document.getElementById("adoption-modal").style.display = "flex";

      // Foca no primeiro campo
      setTimeout(() => {
        const nomeInput = document.getElementById("adoption-nome");
        if (nomeInput) nomeInput.focus();
      }, 100);
    })
    .catch((error) => {
      console.error("Erro ao buscar info do pet:", error);
      // Fallback: abrir modal básico
      criarModalBasico(nomePet, idPet);
    });
}

// Função para buscar informações do pet
async function buscarInfoPet(petId) {
  try {
    const response = await fetch("/api/pets");
    const data = await response.json();

    if (data.pets) {
      const pet = data.pets.find((p) => p.id === petId);
      return pet || {};
    }
    return {};
  } catch (error) {
    console.error("Erro ao buscar pet:", error);
    return {};
  }
}

// Função para criar o modal de adoção completo
function criarModalAdocao(petInfo) {
  const modal = document.getElementById("adoption-modal");
  if (!modal) {
    console.error("Modal de adoção não encontrado!");
    return;
  }

  const imagemPrincipal =
    petInfo.imagens && petInfo.imagens.length > 0
      ? petInfo.imagens.find((img) => img.is_principal) || petInfo.imagens[0]
      : null;

  modal.innerHTML = `
        <div class="adoption-modal-content">
            <div class="adoption-header">
                <div class="pet-image-container">
                    ${
                      imagemPrincipal
                        ? `<img src="${imagemPrincipal.url_imagem}" alt="${
                            petInfo.nome
                          }" class="pet-modal-image">
                           <div class="pet-info-overlay">
                             <h3>${petInfo.nome}</h3>
                             <p>${petInfo.raca_nome} - ${
                            petInfo.especie_nome
                          }</p>
                             <p>Compatibilidade: ${
                               petInfo.compatibilidade || 0
                             }%</p>
                           </div>`
                        : `<div class="pet-placeholder">
                             <span>🐾</span>
                             <h3>${petInfo.nome || "Pet"}</h3>
                           </div>`
                    }
                </div>
                <button class="close-modal-btn" onclick="closeAdoptionModal()">×</button>
            </div>

            <div class="adoption-body">
                <div class="form-section">
                    <h4>📝 Suas Informações</h4>
                    <form id="adoption-form">
                        <input type="hidden" id="adoption-pet-id" value="${
                          petInfo.id || ""
                        }">
                        <input type="hidden" id="adoption-pet-name" value="${
                          petInfo.nome || ""
                        }">

                        <div class="form-grid">
                            <div class="form-group">
                                <label for="adoption-nome">Nome Completo *</label>
                                <input type="text" id="adoption-nome" required placeholder="Seu nome completo">
                            </div>

                            <div class="form-group">
                                <label for="adoption-email">Email *</label>
                                <input type="email" id="adoption-email" required placeholder="seu@email.com">
                            </div>

                            <div class="form-group">
                                <label for="adoption-telefone">Telefone *</label>
                                <input type="tel" id="adoption-telefone" required placeholder="(11) 99999-9999">
                            </div>

                            <div class="form-group">
                                <label for="adoption-whatsapp">WhatsApp</label>
                                <input type="tel" id="adoption-whatsapp" placeholder="(11) 99999-9999">
                            </div>

                            <div class="form-group full-width">
                                <label for="adoption-endereco">Endereço Completo *</label>
                                <input type="text" id="adoption-endereco" required placeholder="Rua, número, bairro">
                            </div>

                            <div class="form-group">
                                <label for="adoption-cidade">Cidade *</label>
                                <input type="text" id="adoption-cidade" required placeholder="Sua cidade">
                            </div>

                            <div class="form-group">
                                <label for="adoption-estado">Estado *</label>
                                <select id="adoption-estado" required>
                                    <option value="">Selecione...</option>
                                    <option value="AC">Acre</option>
                                    <option value="AL">Alagoas</option>
                                    <option value="AP">Amapá</option>
                                    <option value="AM">Amazonas</option>
                                    <option value="BA">Bahia</option>
                                    <option value="CE">Ceará</option>
                                    <option value="DF">Distrito Federal</option>
                                    <option value="ES">Espírito Santo</option>
                                    <option value="GO">Goiás</option>
                                    <option value="MA">Maranhão</option>
                                    <option value="MT">Mato Grosso</option>
                                    <option value="MS">Mato Grosso do Sul</option>
                                    <option value="MG">Minas Gerais</option>
                                    <option value="PA">Pará</option>
                                    <option value="PB">Paraíba</option>
                                    <option value="PR">Paraná</option>
                                    <option value="PE">Pernambuco</option>
                                    <option value="PI">Piauí</option>
                                    <option value="RJ">Rio de Janeiro</option>
                                    <option value="RN">Rio Grande do Norte</option>
                                    <option value="RS">Rio Grande do Sul</option>
                                    <option value="RO">Rondônia</option>
                                    <option value="RR">Roraima</option>
                                    <option value="SC">Santa Catarina</option>
                                    <option value="SP">São Paulo</option>
                                    <option value="SE">Sergipe</option>
                                    <option value="TO">Tocantins</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-section">
                            <h4>🏠 Sua Situação</h4>
                            <div class="form-group">
                                <label for="adoption-tipo-residencia">Tipo de Residência *</label>
                                <select id="adoption-tipo-residencia" required>
                                    <option value="">Selecione...</option>
                                    <option value="casa">Casa</option>
                                    <option value="apartamento">Apartamento</option>
                                    <option value="sítio">Sítio/Chácara</option>
                                    <option value="outro">Outro</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="adoption-tem-quintal">Tem quintal/área externa? *</label>
                                <select id="adoption-tem-quintal" required>
                                    <option value="">Selecione...</option>
                                    <option value="sim">Sim</option>
                                    <option value="nao">Não</option>
                                    <option value="pequeno">Pequeno</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="adoption-moradores">Número de moradores *</label>
                                <input type="number" id="adoption-moradores" required min="1" placeholder="Ex: 3">
                            </div>

                            <div class="form-group">
                                <label for="adoption-criancas">Tem crianças em casa?</label>
                                <select id="adoption-criancas">
                                    <option value="">Selecione...</option>
                                    <option value="nao">Não</option>
                                    <option value="0-5">0-5 anos</option>
                                    <option value="6-12">6-12 anos</option>
                                    <option value="acima-12">Acima de 12 anos</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="adoption-outros-pets">Tem outros pets?</label>
                                <select id="adoption-outros-pets">
                                    <option value="">Selecione...</option>
                                    <option value="nao">Não</option>
                                    <option value="caes">Cães</option>
                                    <option value="gatos">Gatos</option>
                                    <option value="ambos">Cães e Gatos</option>
                                    <option value="outros">Outros</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-section">
                            <h4>💭 Sua Experiência</h4>
                            <div class="form-group full-width">
                                <label for="adoption-experiencia">Já teve pets antes? Conte sua experiência *</label>
                                <textarea id="adoption-experiencia" required placeholder="Conte um pouco sobre sua experiência com animais de estimação..."></textarea>
                            </div>

                            <div class="form-group full-width">
                                <label for="adoption-rotina">Como será a rotina do pet? *</label>
                                <textarea id="adoption-rotina" required placeholder="Descreva como será o dia a dia do pet com você..."></textarea>
                            </div>

                            <div class="form-group full-width">
                                <label for="adoption-motivacao">Por que quer adotar este pet? *</label>
                                <textarea id="adoption-motivacao" required placeholder="Compartilhe o que te motivou a escolher este pet..."></textarea>
                            </div>

                            <div class="form-group full-width">
                                <label for="adoption-mensagem">Mensagem adicional (opcional)</label>
                                <textarea id="adoption-mensagem" placeholder="Alguma informação adicional que gostaria de compartilhar..."></textarea>
                            </div>
                        </div>

                        <div class="form-actions">
                            <button type="button" class="cancel-btn" onclick="closeAdoptionModal()">
                                <span>Cancelar</span>
                            </button>
                            <button type="submit" class="submit-btn">
                                <span>🎯 Enviar Pedido de Adoção</span>
                            </button>
                        </div>

                        <div class="form-footer">
                            <p>📞 Entraremos em contato em até 24 horas para dar continuidade ao processo.</p>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

  // Re-adiciona o event listener ao formulário
  const form = document.getElementById("adoption-form");
  if (form) {
    form.addEventListener("submit", handleAdoptionSubmit);
  }
}

// Função fallback para modal básico
function criarModalBasico(nomePet, idPet) {
  const modal = document.getElementById("adoption-modal");
  if (!modal) return;

  modal.innerHTML = `
        <div class="adoption-modal-content">
            <div class="adoption-header">
                <div class="pet-placeholder">
                    <span>🐾</span>
                    <h3>${nomePet}</h3>
                </div>
                <button class="close-modal-btn" onclick="closeAdoptionModal()">×</button>
            </div>
            
            <div class="adoption-body">
                <p>Formulário de adoção para <strong>${nomePet}</strong></p>
                <p style="color: #666; font-size: 14px; margin-top: 10px;">
                    Para adotar o ${nomePet}, entre em contato conosco pelo telefone (11) 99999-9999
                </p>
            </div>
        </div>
    `;
}

// Função para fechar modal
function closeAdoptionModal() {
  const modal = document.getElementById("adoption-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

// Função para lidar com o envio do formulário de adoção
async function handleAdoptionSubmit(e) {
  e.preventDefault();

  // Obter sessionId do localStorage
  const sessionId =
    localStorage.getItem("petAjudaSessionId") ||
    "sessao-" + Math.random().toString(36).substr(2, 9);

  const petId = document.getElementById("adoption-pet-id").value;
  const petName = document.getElementById("adoption-pet-name").value;
  const nome = document.getElementById("adoption-nome").value;
  const email = document.getElementById("adoption-email").value;
  const telefone = document.getElementById("adoption-telefone").value;
  const whatsapp = document.getElementById("adoption-whatsapp").value;
  const endereco = document.getElementById("adoption-endereco").value;
  const cidade = document.getElementById("adoption-cidade").value;
  const estado = document.getElementById("adoption-estado").value;
  const tipoResidencia = document.getElementById(
    "adoption-tipo-residencia"
  ).value;
  const temQuintal = document.getElementById("adoption-tem-quintal").value;
  const moradores = document.getElementById("adoption-moradores").value;
  const criancas = document.getElementById("adoption-criancas").value;
  const outrosPets = document.getElementById("adoption-outros-pets").value;
  const experiencia = document.getElementById("adoption-experiencia").value;
  const rotina = document.getElementById("adoption-rotina").value;
  const motivacao = document.getElementById("adoption-motivacao").value;
  const mensagem = document.getElementById("adoption-mensagem").value;

  // Validação básica
  const camposObrigatorios = [
    nome,
    email,
    telefone,
    endereco,
    cidade,
    estado,
    tipoResidencia,
    temQuintal,
    moradores,
    experiencia,
    rotina,
    motivacao,
  ];

  if (camposObrigatorios.some((campo) => !campo)) {
    alert("Por favor, preencha todos os campos obrigatórios.");
    return;
  }

  try {
    showAdoptionLoading(petName);

    const response = await fetch("/api/adotar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pet_id: petId,
        pet_nome: petName,
        session_id: sessionId,
        nome: nome,
        email: email,
        telefone: telefone,
        whatsapp: whatsapp,
        endereco: endereco,
        cidade: cidade,
        estado: estado,
        tipo_residencia: tipoResidencia,
        tem_quintal: temQuintal,
        numero_moradores: parseInt(moradores),
        tem_criancas: criancas,
        tem_outros_pets: outrosPets,
        experiencia: experiencia,
        rotina_planejada: rotina,
        motivacao: motivacao,
        mensagem: mensagem,
      }),
    });

    const data = await response.json();

    if (data.success) {
      showAdoptionSuccess(petName, data.message, data.next_steps);
    } else {
      showAdoptionError(data.error || "Erro ao processar adoção");
    }
  } catch (error) {
    console.error("Erro na adoção:", error);
    showAdoptionError("Erro de conexão. Tente novamente.");
  }
}

// Função para mostrar carregamento
function showAdoptionLoading(nomePet) {
  const modal = document.getElementById("adoption-modal");
  if (modal) {
    modal.innerHTML = `
            <div class="adoption-modal-content adoption-loading">
                <h3>Processando adoção...</h3>
                <p>Registrando seu interesse em adotar o ${nomePet}...</p>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
  }
}

// Função para mostrar sucesso
function showAdoptionSuccess(nomePet, message, nextSteps) {
  const modal = document.getElementById("adoption-modal");
  if (modal) {
    modal.innerHTML = `
            <div class="adoption-modal-content adoption-success">
                <h3>🎉 Adoção Registrada!</h3>
                <p><strong>${message}</strong></p>
                <div class="next-steps">
                    <h4>Próximos passos:</h4>
                    <ul>
                        ${
                          nextSteps
                            ? nextSteps
                                .map((step) => `<li>${step}</li>`)
                                .join("")
                            : `
                            <li>Nossa equipe entrará em contato em até 24 horas</li>
                            <li>Prepare os documentos necessários para adoção</li>
                            <li>Agendaremos uma visita para conhecer o pet</li>
                            <li>Será realizada uma entrevista para garantir a melhor compatibilidade</li>
                        `
                        }
                    </ul>
                </div>
                <button class="close-modal" onclick="closeAdoptionModal()">Fechar</button>
            </div>
        `;
  }
}

// Função para mostrar erro
function showAdoptionError(errorMessage) {
  const modal = document.getElementById("adoption-modal");
  if (modal) {
    modal.innerHTML = `
            <div class="adoption-modal-content adoption-error">
                <h3>❌ Ops, algo deu errado!</h3>
                <p>${errorMessage}</p>
                <button class="close-modal" onclick="closeAdoptionModal()">Tentar Novamente</button>
            </div>
        `;
  }
}

// Fechar modal clicando fora
document.addEventListener("click", function (event) {
  const modal = document.getElementById("adoption-modal");
  if (modal && event.target === modal) {
    closeAdoptionModal();
  }
});

// Fechar modal com ESC
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeAdoptionModal();
  }
});
