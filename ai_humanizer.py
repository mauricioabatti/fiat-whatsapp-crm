import random

class AIHumanizer:
    def generate_response(self, phone, user_message):
        responses = [
            "Olá! Sou Felipe da Fiat Globo. Como posso ajudar você hoje?",
            "Oi! Obrigado pelo contato. Em que posso ser útil?",
            "Olá! Felipe aqui da Fiat. Vamos conversar sobre seu próximo carro?"
        ]
        return random.choice(responses)

ai_humanizer = AIHumanizer()
