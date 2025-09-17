# ai_humanizer.py
import random
import re
from datetime import datetime
from typing import Dict, List, Optional
from lead_manager import lead_manager

class AIHumanizer:
    """Sistema de humanização das respostas da IA"""
    
    def __init__(self):
        self.personality_traits = {
            "name": "Felipe Fortes",
            "dealership": "Fiat Globo Itajaí",
            "style": "profissional mas acessível",
            "expertise": "especialista em veículos Fiat"
        }
        
        # Variações de saudações
        self.greetings = {
            "morning": [
                "Bom dia! Aqui é o Felipe, da Fiat Globo Itajaí.",
                "Oi, bom dia! Felipe falando, da Fiat Globo.",
                "Bom dia! Sou o Felipe, consultor da Fiat Globo Itajaí."
            ],
            "afternoon": [
                "Boa tarde! Felipe aqui, da Fiat Globo Itajaí.",
                "Oi, boa tarde! Aqui é o Felipe, da Fiat Globo.",
                "Boa tarde! Felipe falando, consultor da Fiat Globo Itajaí."
            ],
            "evening": [
                "Boa noite! Felipe da Fiat Globo Itajaí.",
                "Oi, boa noite! Aqui é o Felipe, da Fiat Globo.",
                "Boa noite! Sou o Felipe, consultor da Fiat Globo Itajaí."
            ]
        }
        
        # Variações de despedidas
        self.farewells = [
            "Qualquer dúvida, é só chamar!",
            "Estou aqui sempre que precisar!",
            "Fico à disposição para o que precisar!",
            "Pode contar comigo para qualquer esclarecimento!",
            "Estarei aqui quando quiser conversar!"
        ]
        
        # Variações de perguntas de engajamento
        self.engagement_questions = [
            "Tem algum modelo específico em mente?",
            "Qual tipo de carro você está procurando?",
            "Você prefere algo mais econômico ou com mais performance?",
            "Está pensando em trocar seu carro atual?",
            "Que tal conhecer nossas ofertas especiais?",
            "Posso te mostrar algumas opções interessantes?"
        ]
        
        # Palavras-chave para análise de sentimento
        self.sentiment_keywords = {
            "positive": ["ótimo", "excelente", "perfeito", "adorei", "gostei", "interessante", "legal"],
            "negative": ["caro", "ruim", "não gostei", "problema", "difícil", "complicado"],
            "urgent": ["urgente", "rápido", "hoje", "agora", "preciso logo"],
            "casual": ["oi", "olá", "e aí", "beleza", "tranquilo", "de boa"]
        }
    
    def get_time_based_greeting(self) -> str:
        """Retorna saudação baseada no horário"""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return random.choice(self.greetings["morning"])
        elif 12 <= hour < 18:
            return random.choice(self.greetings["afternoon"])
        else:
            return random.choice(self.greetings["evening"])
    
    def analyze_sentiment(self, message: str) -> Dict[str, bool]:
        """Analisa o sentimento da mensagem"""
        message_lower = message.lower()
        
        sentiment = {
            "positive": any(word in message_lower for word in self.sentiment_keywords["positive"]),
            "negative": any(word in message_lower for word in self.sentiment_keywords["negative"]),
            "urgent": any(word in message_lower for word in self.sentiment_keywords["urgent"]),
            "casual": any(word in message_lower for word in self.sentiment_keywords["casual"])
        }
        
        return sentiment
    
    def adapt_tone(self, sentiment: Dict[str, bool]) -> str:
        """Adapta o tom da resposta baseado no sentimento"""
        if sentiment["urgent"]:
            return "direto e eficiente"
        elif sentiment["casual"]:
            return "descontraído e amigável"
        elif sentiment["negative"]:
            return "empático e solucionador"
        elif sentiment["positive"]:
            return "entusiasmado e colaborativo"
        else:
            return "profissional e acolhedor"
    
    def get_conversation_context(self, phone: str) -> str:
        """Obtém contexto da conversa para a IA"""
        context = lead_manager.get_conversation_context(phone, max_messages=8)
        
        if not context:
            return "Esta é a primeira interação com este cliente."
        
        return f"Histórico recente da conversa:\n{context}\n\nContinue a conversa de forma natural, lembrando do que já foi discutido."
    
    def create_enhanced_prompt(self, user_message: str, phone: str) -> str:
        """Cria prompt humanizado para a IA"""
        
        # Analisar sentimento da mensagem
        sentiment = self.analyze_sentiment(user_message)
        tone = self.adapt_tone(sentiment)
        
        # Obter contexto da conversa
        conversation_context = self.get_conversation_context(phone)
        
        # Obter dados do lead
        lead = lead_manager.get_lead(phone)
        lead_info = ""
        if lead:
            lead_info = f"""
Informações do cliente:
- Nome: {lead.get('nome_cliente', 'Não informado')}
- Status atual: {lead.get('status', 'Novo')}
- Score de engajamento: {lead.get('score', 0)}
- Última interação: {lead.get('ultima_interacao', 'Primeira vez')}
"""
        
        # Determinar se é primeira interação
        is_first_interaction = not lead or not lead.get('historico')
        
        prompt = f"""
Você é {self.personality_traits['name']}, um consultor automotivo da {self.personality_traits['dealership']}.

PERSONALIDADE E ESTILO:
- Você é {self.personality_traits['style']} e {self.personality_traits['expertise']}
- Tom da conversa: {tone}
- NUNCA use respostas prontas ou templates
- Varie sempre suas expressões e forma de falar
- Seja genuinamente humano, como se fosse uma conversa real
- Adapte-se ao estilo do cliente (formal/informal)

{lead_info}

{conversation_context}

DIRETRIZES ESPECÍFICAS:
1. Se for a primeira interação, use uma saudação natural e pergunte como pode ajudar
2. Se já conversaram antes, continue naturalmente sem repetir informações
3. Seja proativo mas nunca insistente
4. Use linguagem brasileira natural, sem jargões técnicos desnecessários
5. Faça perguntas inteligentes para qualificar o lead
6. Sempre ofereça valor (informações, test drive, condições especiais)
7. Se não souber algo específico, seja honesto e ofereça verificar

OBJETIVOS:
- Entender a necessidade do cliente
- Qualificar o lead (orçamento, prazo, preferências)
- Sugerir veículos apropriados
- Agendar test drive quando apropriado
- Coletar dados de contato (nome, email)

INFORMAÇÕES IMPORTANTES:
- Endereço: Av. Osvaldo Reis, 1515 – Itajaí/SC
- Horário: Seg-Sex 08:30-18:30, Sáb 08:30-12:30
- Sempre confirme informações importantes (preços, condições) com "vou confirmar com a equipe"

MENSAGEM DO CLIENTE: "{user_message}"

Responda de forma natural, humana e personalizada, como se fosse uma conversa real entre duas pessoas:
"""
        
        return prompt
    
    def add_human_touches(self, ai_response: str) -> str:
        """Adiciona toques humanos à resposta da IA"""
        
        # Remover formatação excessiva
        response = ai_response.strip()
        
        # Adicionar variações naturais ocasionalmente
        natural_fillers = [
            "Olha, ",
            "Veja só, ",
            "Então, ",
            "Bom, ",
            "Ah, ",
            ""  # Às vezes sem filler
        ]
        
        # 30% de chance de adicionar um filler natural
        if random.random() < 0.3 and not response.lower().startswith(('olá', 'oi', 'bom dia', 'boa tarde', 'boa noite')):
            filler = random.choice(natural_fillers)
            response = filler + response
        
        # Adicionar despedida ocasionalmente (20% de chance)
        if random.random() < 0.2 and not response.endswith(('?', '!')):
            farewell = random.choice(self.farewells)
            response += f"\n\n{farewell}"
        
        # Limitar tamanho da resposta para WhatsApp
        if len(response) > 1000:
            # Quebrar em parágrafos menores
            sentences = response.split('. ')
            if len(sentences) > 3:
                response = '. '.join(sentences[:3]) + '.'
                response += f"\n\nQuer que eu detalhe mais algum ponto específico?"
        
        return response
    
    def should_ask_for_info(self, phone: str) -> Optional[str]:
        """Determina se deve pedir informações do cliente"""
        lead = lead_manager.get_lead(phone)
        
        if not lead:
            return None
        
        missing_info = []
        
        if not lead.get('nome_cliente'):
            missing_info.append('nome')
        
        if not lead.get('email'):
            missing_info.append('email')
        
        # Só pedir informações após algumas interações
        if len(lead.get('historico', [])) >= 3 and missing_info:
            if 'nome' in missing_info:
                return "Ah, só para personalizar melhor nosso atendimento, qual seu nome?"
            elif 'email' in missing_info:
                return "Para te enviar informações mais detalhadas, você poderia me passar seu email?"
        
        return None
    
    def extract_client_info(self, message: str) -> Dict[str, str]:
        """Extrai informações do cliente da mensagem"""
        info = {}
        
        # Tentar extrair nome (padrões comuns)
        name_patterns = [
            r"meu nome é (\w+)",
            r"me chamo (\w+)",
            r"sou (\w+)",
            r"eu sou o (\w+)",
            r"eu sou a (\w+)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message.lower())
            if match:
                info['nome_cliente'] = match.group(1).title()
                break
        
        # Tentar extrair email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, message)
        if email_match:
            info['email'] = email_match.group()
        
        return info

# Instância global
ai_humanizer = AIHumanizer()

