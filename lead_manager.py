# lead_manager.py
import os
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app

log = logging.getLogger("fiat-whatsapp")
_lock = threading.Lock()

class LeadManager:
    """Gerenciador de leads com histórico unificado usando arquivos JSON"""
    
    def __init__(self, leads_dir: str = "leads"):
        self.leads_dir = leads_dir
        os.makedirs(leads_dir, exist_ok=True)
    
    def _get_lead_file_path(self, phone: str) -> str:
        """Retorna o caminho do arquivo JSON para um telefone"""
        # Remove caracteres especiais e espaços do telefone
        clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        return os.path.join(self.leads_dir, f"{clean_phone}.json")
    
    def _atomic_write(self, path: str, data: dict):
        """Escreve dados de forma atômica para evitar corrupção"""
        tmp_path = path + ".tmp"
        with _lock:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
    
    def get_lead(self, phone: str) -> Optional[Dict[str, Any]]:
        """Recupera dados de um lead pelo telefone"""
        file_path = self._get_lead_file_path(phone)
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Erro ao ler lead {phone}: {e}")
            return None
    
    def create_or_update_lead(self, phone: str, **kwargs) -> Dict[str, Any]:
        """Cria ou atualiza um lead"""
        lead = self.get_lead(phone)
        now = datetime.now().isoformat()
        
        if lead is None:
            # Criar novo lead
            lead = {
                "telefone": phone,
                "nome_cliente": kwargs.get("nome_cliente", ""),
                "email": kwargs.get("email", ""),
                "status": kwargs.get("status", "Novo"),
                "data_criacao": now,
                "ultima_interacao": now,
                "vendedor_responsavel": kwargs.get("vendedor_responsavel", "Felipe Fortes"),
                "notas": [],
                "historico": [],
                "agendamentos": [],
                "score": 0,
                "tags": []
            }
            log.info(f"Novo lead criado: {phone}")
        else:
            # Atualizar lead existente
            lead["ultima_interacao"] = now
            for key, value in kwargs.items():
                if key in lead and value is not None:
                    lead[key] = value
        
        self._atomic_write(self._get_lead_file_path(phone), lead)
        return lead
    
    def add_interaction(self, phone: str, direction: str, message: str, message_type: str = "texto") -> Dict[str, Any]:
        """Adiciona uma interação ao histórico do lead"""
        lead = self.get_lead(phone)
        if lead is None:
            lead = self.create_or_update_lead(phone)
        
        interaction = {
            "direcao": direction,  # "Entrada" ou "Saída"
            "mensagem": message,
            "tipo_mensagem": message_type,
            "timestamp": datetime.now().isoformat()
        }
        
        lead["historico"].append(interaction)
        lead["ultima_interacao"] = interaction["timestamp"]
        
        # Atualizar score baseado na interação
        self._update_lead_score(lead, direction, message)
        
        self._atomic_write(self._get_lead_file_path(phone), lead)
        return lead
    
    def _update_lead_score(self, lead: Dict[str, Any], direction: str, message: str):
        """Atualiza o score do lead baseado na interação"""
        message_lower = message.lower()
        
        # Pontuação por palavras-chave
        keywords_scores = {
            "financiamento": 15,
            "preço": 10,
            "preco": 10,
            "test drive": 30,
            "teste": 20,
            "agendar": 25,
            "comprar": 40,
            "quando": 10,
            "disponível": 8,
            "disponivel": 8,
            "cores": 5,
            "modelo": 8
        }
        
        for keyword, score in keywords_scores.items():
            if keyword in message_lower:
                lead["score"] += score
        
        # Pontuação por direção da mensagem
        if direction == "Entrada":
            lead["score"] += 2  # Cliente respondeu
        
        # Limitar score máximo
        lead["score"] = min(lead["score"], 200)
    
    def add_note(self, phone: str, note: str, author: str = "Sistema") -> Dict[str, Any]:
        """Adiciona uma nota ao lead"""
        lead = self.get_lead(phone)
        if lead is None:
            lead = self.create_or_update_lead(phone)
        
        note_entry = {
            "texto": note,
            "autor": author,
            "timestamp": datetime.now().isoformat()
        }
        
        lead["notas"].append(note_entry)
        self._atomic_write(self._get_lead_file_path(phone), lead)
        return lead
    
    def update_status(self, phone: str, new_status: str) -> Dict[str, Any]:
        """Atualiza o status do lead"""
        lead = self.get_lead(phone)
        if lead is None:
            return None
        
        old_status = lead.get("status", "Novo")
        lead["status"] = new_status
        lead["ultima_interacao"] = datetime.now().isoformat()
        
        # Adicionar nota automática sobre mudança de status
        self.add_note(phone, f"Status alterado de '{old_status}' para '{new_status}'", "Sistema")
        
        self._atomic_write(self._get_lead_file_path(phone), lead)
        return lead
    
    def get_all_leads(self) -> List[Dict[str, Any]]:
        """Retorna todos os leads"""
        leads = []
        
        if not os.path.exists(self.leads_dir):
            return leads
        
        for filename in os.listdir(self.leads_dir):
            if filename.endswith(".json"):
                phone = filename.replace(".json", "")
                # Reconstruir telefone com +
                if not phone.startswith("+"):
                    phone = "+" + phone
                
                lead = self.get_lead(phone)
                if lead:
                    leads.append(lead)
        
        return leads
    
    def get_leads_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Retorna leads filtrados por status"""
        all_leads = self.get_all_leads()
        return [lead for lead in all_leads if lead.get("status") == status]
    
    def get_hot_leads(self, min_score: int = 50) -> List[Dict[str, Any]]:
        """Retorna leads 'quentes' baseado no score"""
        all_leads = self.get_all_leads()
        hot_leads = [lead for lead in all_leads if lead.get("score", 0) >= min_score]
        return sorted(hot_leads, key=lambda x: x.get("score", 0), reverse=True)
    
    def get_inactive_leads(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Retorna leads inativos há mais de X horas"""
        all_leads = self.get_all_leads()
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        inactive_leads = []
        for lead in all_leads:
            try:
                last_interaction = datetime.fromisoformat(lead.get("ultima_interacao", ""))
                if last_interaction < cutoff_time and lead.get("status") not in ["Vendido", "Perdido"]:
                    inactive_leads.append(lead)
            except:
                continue
        
        return inactive_leads
    
    def get_conversation_context(self, phone: str, max_messages: int = 10) -> str:
        """Retorna o contexto da conversa para a IA"""
        lead = self.get_lead(phone)
        if not lead or not lead.get("historico"):
            return ""
        
        # Pegar as últimas mensagens
        recent_messages = lead["historico"][-max_messages:]
        
        context_lines = []
        for msg in recent_messages:
            direction = "Cliente" if msg["direcao"] == "Entrada" else "Vendedor"
            context_lines.append(f"{direction}: {msg['mensagem']}")
        
        return "\n".join(context_lines)

# Instância global do gerenciador
lead_manager = LeadManager()

