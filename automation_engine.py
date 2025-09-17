# automation_engine.py
import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import current_app
from lead_manager import lead_manager
from ai_humanizer import ai_humanizer

log = logging.getLogger("fiat-whatsapp")

class AutomationEngine:
    """Sistema de automação de follow-up e engajamento"""
    
    def __init__(self):
        self.automation_rules = self._load_automation_rules()
        self.running = False
        self.thread = None
        
    def _load_automation_rules(self) -> List[Dict[str, Any]]:
        """Carrega regras de automação"""
        return [
            {
                "name": "follow_up_inativo_5h",
                "description": "Follow-up para leads inativos há 5 horas",
                "condition": {
                    "inactive_hours": 5,
                    "status_not_in": ["Vendido", "Perdido"],
                    "max_follow_ups": 3
                },
                "action": {
                    "type": "send_message",
                    "templates": [
                        "Oi! Só passando para saber se você teve a chance de ver as informações que te enviei. Alguma dúvida que posso esclarecer?",
                        "Olá! Notei que conversamos mais cedo sobre os carros. Tem alguma pergunta que posso ajudar a responder?",
                        "Oi! Queria saber se você gostaria de mais detalhes sobre algum modelo específico que conversamos.",
                        "Olá! Caso tenha ficado alguma dúvida sobre nossas ofertas, estou aqui para ajudar!"
                    ]
                }
            },
            {
                "name": "lembrete_test_drive",
                "description": "Lembrete 24h antes do test drive",
                "condition": {
                    "status": "Agendado",
                    "hours_before_appointment": 24
                },
                "action": {
                    "type": "send_message",
                    "templates": [
                        "Oi! Só para confirmar seu test drive amanhã. Nosso endereço é Av. Osvaldo Reis, 1515 - Itajaí. Estamos te esperando!",
                        "Olá! Lembrete do seu test drive marcado para amanhã. Qualquer imprevisto, é só me avisar!",
                        "Oi! Confirmando seu test drive de amanhã. Vai ser ótimo te conhecer pessoalmente!"
                    ]
                }
            },
            {
                "name": "reativacao_lead_frio",
                "description": "Reativação de leads frios (7 dias sem interação)",
                "condition": {
                    "inactive_hours": 168,  # 7 dias
                    "status_not_in": ["Vendido", "Perdido"],
                    "score_min": 10
                },
                "action": {
                    "type": "send_message",
                    "templates": [
                        "Oi! Faz um tempo que não conversamos. Temos algumas ofertas especiais novas que podem te interessar. Quer dar uma olhada?",
                        "Olá! Apareceram algumas condições especiais de financiamento que talvez sejam interessantes para você. Posso te contar?",
                        "Oi! Chegaram alguns carros novos na loja que podem ser do seu perfil. Quer que eu te mande as informações?"
                    ]
                }
            },
            {
                "name": "qualificacao_lead_quente",
                "description": "Qualificação de leads com alto score",
                "condition": {
                    "score_min": 50,
                    "status": "Novo",
                    "no_recent_qualification": True
                },
                "action": {
                    "type": "send_message",
                    "templates": [
                        "Oi! Vejo que você tem bastante interesse em nossos carros. Que tal agendarmos um test drive para você conhecer melhor?",
                        "Olá! Pelo seu interesse, acredito que temos o carro ideal para você. Podemos conversar sobre as condições?",
                        "Oi! Notei seu interesse em nossos veículos. Quer que eu prepare uma proposta personalizada para você?"
                    ]
                }
            }
        ]
    
    def start_automation(self):
        """Inicia o motor de automação"""
        if self.running:
            log.warning("Automação já está rodando")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._automation_loop, daemon=True)
        self.thread.start()
        log.info("Motor de automação iniciado")
    
    def stop_automation(self):
        """Para o motor de automação"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        log.info("Motor de automação parado")
    
    def _automation_loop(self):
        """Loop principal da automação"""
        while self.running:
            try:
                self._process_automation_rules()
                # Aguardar 5 minutos antes da próxima verificação
                time.sleep(300)  # 5 minutos
            except Exception as e:
                log.error(f"Erro no loop de automação: {e}")
                time.sleep(60)  # Aguardar 1 minuto em caso de erro
    
    def _process_automation_rules(self):
        """Processa todas as regras de automação"""
        all_leads = lead_manager.get_all_leads()
        
        for rule in self.automation_rules:
            try:
                eligible_leads = self._find_eligible_leads(all_leads, rule)
                
                for lead in eligible_leads:
                    if self._should_execute_rule(lead, rule):
                        self._execute_rule_action(lead, rule)
                        
            except Exception as e:
                log.error(f"Erro ao processar regra {rule['name']}: {e}")
    
    def _find_eligible_leads(self, leads: List[Dict], rule: Dict) -> List[Dict]:
        """Encontra leads elegíveis para uma regra específica"""
        eligible = []
        condition = rule["condition"]
        
        for lead in leads:
            if self._lead_matches_condition(lead, condition):
                eligible.append(lead)
        
        return eligible
    
    def _lead_matches_condition(self, lead: Dict, condition: Dict) -> bool:
        """Verifica se um lead atende às condições da regra"""
        
        # Verificar status
        if "status" in condition:
            if lead.get("status") != condition["status"]:
                return False
        
        if "status_not_in" in condition:
            if lead.get("status") in condition["status_not_in"]:
                return False
        
        # Verificar score mínimo
        if "score_min" in condition:
            if lead.get("score", 0) < condition["score_min"]:
                return False
        
        # Verificar inatividade
        if "inactive_hours" in condition:
            last_interaction = lead.get("ultima_interacao")
            if last_interaction:
                try:
                    last_time = datetime.fromisoformat(last_interaction)
                    hours_inactive = (datetime.now() - last_time).total_seconds() / 3600
                    if hours_inactive < condition["inactive_hours"]:
                        return False
                except:
                    return False
        
        # Verificar máximo de follow-ups
        if "max_follow_ups" in condition:
            follow_up_count = self._count_follow_ups(lead)
            if follow_up_count >= condition["max_follow_ups"]:
                return False
        
        return True
    
    def _should_execute_rule(self, lead: Dict, rule: Dict) -> bool:
        """Verifica se deve executar a regra para este lead"""
        
        # Verificar se já executou esta regra recentemente
        last_automation = self._get_last_automation(lead, rule["name"])
        if last_automation:
            # Não executar a mesma regra mais de uma vez por dia
            time_since_last = datetime.now() - last_automation
            if time_since_last < timedelta(hours=24):
                return False
        
        return True
    
    def _execute_rule_action(self, lead: Dict, rule: Dict):
        """Executa a ação da regra"""
        action = rule["action"]
        
        if action["type"] == "send_message":
            self._send_automated_message(lead, rule)
        
        # Registrar que a automação foi executada
        self._record_automation_execution(lead, rule["name"])
    
    def _send_automated_message(self, lead: Dict, rule: Dict):
        """Envia mensagem automatizada"""
        import random
        
        templates = rule["action"]["templates"]
        message = random.choice(templates)
        
        # Personalizar mensagem se tiver nome do cliente
        if lead.get("nome_cliente"):
            # Adicionar nome de forma natural
            if not message.startswith(("Oi", "Olá")):
                message = f"Oi, {lead['nome_cliente']}! " + message.lower()
            else:
                message = message.replace("Oi!", f"Oi, {lead['nome_cliente']}!")
                message = message.replace("Olá!", f"Olá, {lead['nome_cliente']}!")
        
        # Registrar a mensagem no histórico
        lead_manager.add_interaction(
            phone=lead["telefone"],
            direction="Saída",
            message=message,
            message_type="automacao"
        )
        
        # Tentar enviar via Twilio se configurado
        self._try_send_via_twilio(lead["telefone"], message)
        
        log.info(f"Mensagem automática enviada para {lead['telefone']}: {rule['name']}")
    
    def _try_send_via_twilio(self, phone: str, message: str):
        """Tenta enviar mensagem via Twilio"""
        try:
            # Importar aqui para evitar dependência circular
            from routes import send_via_twilio_api
            
            # Tentar enviar se as configurações estiverem disponíveis
            if hasattr(current_app, 'config'):
                success = send_via_twilio_api(phone, message)
                if success:
                    log.info(f"Mensagem automática enviada via Twilio para {phone}")
                else:
                    log.warning(f"Falha ao enviar mensagem automática via Twilio para {phone}")
        except Exception as e:
            log.error(f"Erro ao enviar mensagem automática via Twilio: {e}")
    
    def _count_follow_ups(self, lead: Dict) -> int:
        """Conta quantos follow-ups automáticos foram enviados"""
        count = 0
        for interaction in lead.get("historico", []):
            if (interaction.get("direcao") == "Saída" and 
                interaction.get("tipo_mensagem") == "automacao"):
                count += 1
        return count
    
    def _get_last_automation(self, lead: Dict, rule_name: str) -> Optional[datetime]:
        """Obtém a data da última execução de uma regra específica"""
        automations = lead.get("automations", {})
        last_execution = automations.get(rule_name)
        
        if last_execution:
            try:
                return datetime.fromisoformat(last_execution)
            except:
                return None
        
        return None
    
    def _record_automation_execution(self, lead: Dict, rule_name: str):
        """Registra a execução de uma automação"""
        if "automations" not in lead:
            lead["automations"] = {}
        
        lead["automations"][rule_name] = datetime.now().isoformat()
        
        # Salvar o lead atualizado
        lead_manager._atomic_write(
            lead_manager._get_lead_file_path(lead["telefone"]),
            lead
        )
    
    def get_automation_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das automações"""
        all_leads = lead_manager.get_all_leads()
        
        stats = {
            "total_automations_sent": 0,
            "automations_by_rule": {},
            "leads_with_automations": 0
        }
        
        for lead in all_leads:
            automations = lead.get("automations", {})
            if automations:
                stats["leads_with_automations"] += 1
                
                for rule_name in automations:
                    stats["automations_by_rule"][rule_name] = stats["automations_by_rule"].get(rule_name, 0) + 1
                    stats["total_automations_sent"] += 1
        
        return stats
    
    def manual_follow_up(self, phone: str, message: str) -> bool:
        """Envia follow-up manual"""
        try:
            # Registrar a mensagem
            lead_manager.add_interaction(
                phone=phone,
                direction="Saída",
                message=message,
                message_type="manual"
            )
            
            # Tentar enviar via Twilio
            self._try_send_via_twilio(phone, message)
            
            log.info(f"Follow-up manual enviado para {phone}")
            return True
            
        except Exception as e:
            log.error(f"Erro ao enviar follow-up manual: {e}")
            return False

# Instância global
automation_engine = AutomationEngine()

