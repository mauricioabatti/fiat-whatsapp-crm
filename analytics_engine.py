# analytics_engine.py
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from lead_manager import lead_manager

class AnalyticsEngine:
    """Sistema de analytics e relatórios para identificar oportunidades de vendas"""
    
    def __init__(self):
        self.vehicle_keywords = {
            "pulse": ["pulse"],
            "toro": ["toro"],
            "strada": ["strada"],
            "argo": ["argo"],
            "cronos": ["cronos"],
            "fastback": ["fastback"],
            "mobi": ["mobi"],
            "fiorino": ["fiorino"],
            "ducato": ["ducato"]
        }
        
        self.intent_keywords = {
            "compra": ["comprar", "adquirir", "levar", "fechar negócio", "finalizar"],
            "financiamento": ["financiar", "financiamento", "parcelar", "entrada", "prestação"],
            "test_drive": ["test drive", "teste", "dirigir", "experimentar", "conhecer"],
            "preco": ["preço", "preco", "valor", "custa", "quanto"],
            "troca": ["trocar", "troca", "dar entrada", "usado"],
            "urgencia": ["urgente", "rápido", "hoje", "agora", "logo"]
        }
    
    def generate_full_report(self) -> Dict[str, Any]:
        """Gera relatório completo de analytics"""
        all_leads = lead_manager.get_all_leads()
        
        return {
            "overview": self._get_overview_metrics(all_leads),
            "funnel": self._get_funnel_analysis(all_leads),
            "engagement": self._get_engagement_analysis(all_leads),
            "vehicles": self._get_vehicle_interest_analysis(all_leads),
            "opportunities": self._identify_sales_opportunities(all_leads),
            "performance": self._get_performance_metrics(all_leads),
            "trends": self._get_trend_analysis(all_leads)
        }
    
    def _get_overview_metrics(self, leads: List[Dict]) -> Dict[str, Any]:
        """Métricas gerais de overview"""
        total_leads = len(leads)
        
        if total_leads == 0:
            return {
                "total_leads": 0,
                "conversion_rate": 0,
                "avg_score": 0,
                "hot_leads": 0,
                "active_leads": 0
            }
        
        # Contar por status
        status_counts = Counter(lead.get("status", "Novo") for lead in leads)
        
        # Taxa de conversão
        converted = status_counts.get("Vendido", 0)
        conversion_rate = round((converted / total_leads) * 100, 1) if total_leads > 0 else 0
        
        # Score médio
        scores = [lead.get("score", 0) for lead in leads]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        
        # Leads quentes (score >= 50)
        hot_leads = len([lead for lead in leads if lead.get("score", 0) >= 50])
        
        # Leads ativos (interação nas últimas 24h)
        now = datetime.now()
        active_leads = 0
        for lead in leads:
            try:
                last_interaction = datetime.fromisoformat(lead.get("ultima_interacao", ""))
                if (now - last_interaction).total_seconds() < 86400:  # 24 horas
                    active_leads += 1
            except:
                continue
        
        return {
            "total_leads": total_leads,
            "conversion_rate": conversion_rate,
            "avg_score": avg_score,
            "hot_leads": hot_leads,
            "active_leads": active_leads,
            "status_distribution": dict(status_counts)
        }
    
    def _get_funnel_analysis(self, leads: List[Dict]) -> Dict[str, Any]:
        """Análise do funil de vendas"""
        funnel_stages = ["Novo", "Em Atendimento", "Proposta Enviada", "Agendado", "Vendido", "Perdido"]
        
        stage_counts = {}
        for stage in funnel_stages:
            stage_counts[stage] = len([lead for lead in leads if lead.get("status") == stage])
        
        # Calcular taxas de conversão entre estágios
        conversion_rates = {}
        for i in range(len(funnel_stages) - 2):  # Excluir "Perdido"
            current_stage = funnel_stages[i]
            next_stage = funnel_stages[i + 1]
            
            current_count = stage_counts[current_stage]
            next_count = stage_counts[next_stage]
            
            if current_count > 0:
                rate = round((next_count / current_count) * 100, 1)
            else:
                rate = 0
            
            conversion_rates[f"{current_stage}_to_{next_stage}"] = rate
        
        return {
            "stage_counts": stage_counts,
            "conversion_rates": conversion_rates,
            "bottlenecks": self._identify_bottlenecks(stage_counts, conversion_rates)
        }
    
    def _identify_bottlenecks(self, stage_counts: Dict, conversion_rates: Dict) -> List[str]:
        """Identifica gargalos no funil"""
        bottlenecks = []
        
        # Identificar estágios com baixa conversão (< 30%)
        for stage_conversion, rate in conversion_rates.items():
            if rate < 30 and rate > 0:
                bottlenecks.append(f"Baixa conversão: {stage_conversion} ({rate}%)")
        
        # Identificar acúmulo de leads em um estágio
        total_leads = sum(stage_counts.values())
        for stage, count in stage_counts.items():
            if count > 0 and total_leads > 0:
                percentage = (count / total_leads) * 100
                if percentage > 40 and stage not in ["Novo", "Vendido"]:
                    bottlenecks.append(f"Acúmulo em {stage}: {percentage:.1f}% dos leads")
        
        return bottlenecks
    
    def _get_engagement_analysis(self, leads: List[Dict]) -> Dict[str, Any]:
        """Análise de engajamento dos leads"""
        
        # Distribuição de scores
        score_ranges = {
            "0-20": 0,
            "21-50": 0,
            "51-100": 0,
            "100+": 0
        }
        
        total_interactions = 0
        leads_with_interactions = 0
        
        for lead in leads:
            score = lead.get("score", 0)
            
            if score <= 20:
                score_ranges["0-20"] += 1
            elif score <= 50:
                score_ranges["21-50"] += 1
            elif score <= 100:
                score_ranges["51-100"] += 1
            else:
                score_ranges["100+"] += 1
            
            # Contar interações
            interactions = len(lead.get("historico", []))
            if interactions > 0:
                total_interactions += interactions
                leads_with_interactions += 1
        
        avg_interactions = round(total_interactions / leads_with_interactions, 1) if leads_with_interactions > 0 else 0
        
        return {
            "score_distribution": score_ranges,
            "avg_interactions_per_lead": avg_interactions,
            "engagement_levels": self._classify_engagement_levels(leads)
        }
    
    def _classify_engagement_levels(self, leads: List[Dict]) -> Dict[str, int]:
        """Classifica níveis de engajamento"""
        levels = {
            "Alto": 0,      # Score >= 50 e múltiplas interações
            "Médio": 0,     # Score 20-49 ou algumas interações
            "Baixo": 0      # Score < 20 e poucas interações
        }
        
        for lead in leads:
            score = lead.get("score", 0)
            interactions = len(lead.get("historico", []))
            
            if score >= 50 or interactions >= 5:
                levels["Alto"] += 1
            elif score >= 20 or interactions >= 2:
                levels["Médio"] += 1
            else:
                levels["Baixo"] += 1
        
        return levels
    
    def _get_vehicle_interest_analysis(self, leads: List[Dict]) -> Dict[str, Any]:
        """Análise de interesse por veículos"""
        vehicle_mentions = Counter()
        intent_analysis = defaultdict(list)
        
        for lead in leads:
            phone = lead.get("telefone", "")
            
            # Analisar todas as mensagens do lead
            for interaction in lead.get("historico", []):
                if interaction.get("direcao") == "Entrada":  # Mensagens do cliente
                    message = interaction.get("mensagem", "").lower()
                    
                    # Contar menções de veículos
                    for vehicle, keywords in self.vehicle_keywords.items():
                        if any(keyword in message for keyword in keywords):
                            vehicle_mentions[vehicle] += 1
                    
                    # Analisar intenções
                    for intent, keywords in self.intent_keywords.items():
                        if any(keyword in message for keyword in keywords):
                            intent_analysis[intent].append(phone)
        
        # Remover duplicatas nas intenções
        for intent in intent_analysis:
            intent_analysis[intent] = list(set(intent_analysis[intent]))
        
        return {
            "vehicle_popularity": dict(vehicle_mentions.most_common()),
            "intent_distribution": {intent: len(phones) for intent, phones in intent_analysis.items()},
            "high_intent_leads": self._identify_high_intent_leads(intent_analysis)
        }
    
    def _identify_high_intent_leads(self, intent_analysis: Dict) -> List[Dict]:
        """Identifica leads com alta intenção de compra"""
        high_intent_leads = []
        
        # Leads que mencionaram compra ou urgência
        high_intent_phones = set()
        for intent in ["compra", "urgencia", "financiamento"]:
            high_intent_phones.update(intent_analysis.get(intent, []))
        
        for phone in high_intent_phones:
            lead = lead_manager.get_lead(phone)
            if lead:
                high_intent_leads.append({
                    "phone": phone,
                    "name": lead.get("nome_cliente", "Cliente"),
                    "status": lead.get("status", "Novo"),
                    "score": lead.get("score", 0),
                    "last_interaction": lead.get("ultima_interacao", "")
                })
        
        # Ordenar por score
        high_intent_leads.sort(key=lambda x: x["score"], reverse=True)
        
        return high_intent_leads[:10]  # Top 10
    
    def _identify_sales_opportunities(self, leads: List[Dict]) -> Dict[str, List[Dict]]:
        """Identifica oportunidades de vendas específicas"""
        opportunities = {
            "ready_to_buy": [],      # Prontos para comprar
            "need_follow_up": [],    # Precisam de follow-up
            "price_sensitive": [],   # Sensíveis a preço
            "test_drive_ready": [],  # Prontos para test drive
            "lost_opportunities": [] # Oportunidades perdidas
        }
        
        now = datetime.now()
        
        for lead in leads:
            phone = lead.get("telefone", "")
            score = lead.get("score", 0)
            status = lead.get("status", "Novo")
            
            # Analisar mensagens para identificar padrões
            messages = []
            for interaction in lead.get("historico", []):
                if interaction.get("direcao") == "Entrada":
                    messages.append(interaction.get("mensagem", "").lower())
            
            all_messages = " ".join(messages)
            
            # Ready to buy: alta pontuação + menções de compra/financiamento
            if (score >= 70 and 
                any(keyword in all_messages for keyword in ["comprar", "financiar", "fechar"]) and
                status not in ["Vendido", "Perdido"]):
                opportunities["ready_to_buy"].append(self._create_opportunity_record(lead, "Alta intenção de compra"))
            
            # Need follow-up: leads inativos com potencial
            try:
                last_interaction = datetime.fromisoformat(lead.get("ultima_interacao", ""))
                hours_inactive = (now - last_interaction).total_seconds() / 3600
                
                if (hours_inactive > 48 and score >= 30 and 
                    status not in ["Vendido", "Perdido"]):
                    opportunities["need_follow_up"].append(self._create_opportunity_record(lead, f"Inativo há {int(hours_inactive)}h"))
            except:
                pass
            
            # Price sensitive: mencionaram preço múltiplas vezes
            price_mentions = all_messages.count("preço") + all_messages.count("preco") + all_messages.count("valor")
            if price_mentions >= 2 and status not in ["Vendido", "Perdido"]:
                opportunities["price_sensitive"].append(self._create_opportunity_record(lead, f"{price_mentions} menções de preço"))
            
            # Test drive ready: interessados mas não agendaram
            if (any(keyword in all_messages for keyword in ["test", "dirigir", "conhecer"]) and
                status not in ["Agendado", "Vendido", "Perdido"]):
                opportunities["test_drive_ready"].append(self._create_opportunity_record(lead, "Interesse em test drive"))
            
            # Lost opportunities: leads quentes que viraram perdidos
            if status == "Perdido" and score >= 50:
                opportunities["lost_opportunities"].append(self._create_opportunity_record(lead, f"Lead quente perdido (score: {score})"))
        
        # Limitar a 10 itens por categoria e ordenar por score
        for category in opportunities:
            opportunities[category] = sorted(opportunities[category], key=lambda x: x["score"], reverse=True)[:10]
        
        return opportunities
    
    def _create_opportunity_record(self, lead: Dict, reason: str) -> Dict:
        """Cria registro de oportunidade"""
        return {
            "phone": lead.get("telefone", ""),
            "name": lead.get("nome_cliente", "Cliente"),
            "status": lead.get("status", "Novo"),
            "score": lead.get("score", 0),
            "reason": reason,
            "last_interaction": lead.get("ultima_interacao", "")
        }
    
    def _get_performance_metrics(self, leads: List[Dict]) -> Dict[str, Any]:
        """Métricas de performance do sistema"""
        
        # Tempo médio de resposta (simulado - seria calculado com timestamps reais)
        avg_response_time = 0.5  # Assumindo 30 minutos em média
        
        # Leads por período
        now = datetime.now()
        periods = {
            "today": 0,
            "this_week": 0,
            "this_month": 0
        }
        
        for lead in leads:
            try:
                created_date = datetime.fromisoformat(lead.get("data_criacao", ""))
                
                if created_date.date() == now.date():
                    periods["today"] += 1
                
                if (now - created_date).days <= 7:
                    periods["this_week"] += 1
                
                if (now - created_date).days <= 30:
                    periods["this_month"] += 1
            except:
                continue
        
        return {
            "avg_response_time_hours": avg_response_time,
            "leads_by_period": periods,
            "automation_stats": self._get_automation_performance()
        }
    
    def _get_automation_performance(self) -> Dict[str, Any]:
        """Performance das automações"""
        # Importar aqui para evitar dependência circular
        try:
            from automation_engine import automation_engine
            return automation_engine.get_automation_stats()
        except:
            return {
                "total_automations_sent": 0,
                "automations_by_rule": {},
                "leads_with_automations": 0
            }
    
    def _get_trend_analysis(self, leads: List[Dict]) -> Dict[str, Any]:
        """Análise de tendências"""
        
        # Tendência de criação de leads (últimos 7 dias)
        daily_leads = defaultdict(int)
        now = datetime.now()
        
        for i in range(7):
            date = (now - timedelta(days=i)).date()
            daily_leads[date.isoformat()] = 0
        
        for lead in leads:
            try:
                created_date = datetime.fromisoformat(lead.get("data_criacao", "")).date()
                if created_date.isoformat() in daily_leads:
                    daily_leads[created_date.isoformat()] += 1
            except:
                continue
        
        # Tendência de conversão
        conversion_trend = self._calculate_conversion_trend(leads)
        
        return {
            "daily_leads_last_7_days": dict(daily_leads),
            "conversion_trend": conversion_trend,
            "peak_hours": self._analyze_peak_hours(leads)
        }
    
    def _calculate_conversion_trend(self, leads: List[Dict]) -> str:
        """Calcula tendência de conversão"""
        # Simplificado - comparar últimos 7 dias com 7 dias anteriores
        now = datetime.now()
        
        recent_converted = 0
        recent_total = 0
        previous_converted = 0
        previous_total = 0
        
        for lead in leads:
            try:
                created_date = datetime.fromisoformat(lead.get("data_criacao", ""))
                days_ago = (now - created_date).days
                
                if days_ago <= 7:
                    recent_total += 1
                    if lead.get("status") == "Vendido":
                        recent_converted += 1
                elif 8 <= days_ago <= 14:
                    previous_total += 1
                    if lead.get("status") == "Vendido":
                        previous_converted += 1
            except:
                continue
        
        if previous_total > 0 and recent_total > 0:
            recent_rate = (recent_converted / recent_total) * 100
            previous_rate = (previous_converted / previous_total) * 100
            
            if recent_rate > previous_rate:
                return "Melhorando"
            elif recent_rate < previous_rate:
                return "Piorando"
            else:
                return "Estável"
        
        return "Dados insuficientes"
    
    def _analyze_peak_hours(self, leads: List[Dict]) -> List[int]:
        """Analisa horários de pico de atividade"""
        hour_counts = defaultdict(int)
        
        for lead in leads:
            for interaction in lead.get("historico", []):
                if interaction.get("direcao") == "Entrada":
                    try:
                        timestamp = datetime.fromisoformat(interaction.get("timestamp", ""))
                        hour_counts[timestamp.hour] += 1
                    except:
                        continue
        
        # Retornar top 3 horários
        top_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        return [hour for hour, count in top_hours]

# Instância global
analytics_engine = AnalyticsEngine()

