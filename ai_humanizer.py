import os
import openai
from datetime import datetime
import random

class AIHumanizer:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
    
    def generate_response(self, phone, user_message):
        """Gera resposta humanizada usando OpenAI"""
        try:
            # Prompt humanizado para Felipe Fortes
            system_prompt = """Você é Felipe Fortes, vendedor da Fiat Globo Itajaí. 
            Seja natural, amigável e profissional. Varie suas respostas, nunca use respostas prontas.
            Ajude com informações sobre carros Fiat, preços, test drives e financiamento.
            Seja educado mas não robótico. Use linguagem brasileira natural."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Resposta de fallback se OpenAI falhar
            fallback_responses = [
                "Olá! Sou Felipe da Fiat Globo. Como posso ajudar você hoje?",
                "Oi! Obrigado pelo contato. Em que posso ser útil?",
                "Olá! Felipe aqui da Fiat. Vamos conversar sobre seu próximo carro?"
            ]
            return random.choice(fallback_responses)

# Instância global
ai_humanizer = AIHumanizer()
