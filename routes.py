# routes_new.py - VERSÃO INTEGRADA COM TODAS AS FUNCIONALIDADES
import os, csv, json, logging, threading, random, re
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape

from flask import Blueprint, current_app, request, Response, jsonify, render_template, abort
from twilio.rest import Client as TwilioClient

from catalog import tentar_responder_com_catalogo
from calendar_helpers import (
    build_gcal, is_slot_available, create_event, freebusy, business_hours_for,
    get_available_slots, format_available_times
)
from lead_manager import lead_manager
from ai_humanizer import ai_humanizer
from automation_engine import automation_engine
from analytics_engine import analytics_engine

bp = Blueprint("routes", __name__)
log = logging.getLogger("fiat-whatsapp")

# =========================
# Twilio helpers (envio via API)
# =========================
def _twilio_client():
    sid   = current_app.config.get("TWILIO_ACCOUNT_SID")
    token = current_app.config.get("TWILIO_AUTH_TOKEN")
    if not (sid and token): return None
    try: return TwilioClient(sid, token)
    except Exception:
        log.exception("Falha ao criar cliente Twilio"); return None

def send_via_twilio_api(to_phone_e164: str, body: str) -> bool:
    if not current_app.config.get("TWILIO_WHATSAPP_FROM"):
        return False
    client = _twilio_client()
    if not client: return False
    try:
        to_fmt = f"whatsapp:{to_phone_e164}" if not str(to_phone_e164).startswith("whatsapp:") else to_phone_e164
        msg = client.messages.create(
            from_=current_app.config["TWILIO_WHATSAPP_FROM"],
            to=to_fmt,
            body=body
        )
        log.info(f"Twilio API enviado: sid={msg.sid}")
        return True
    except Exception:
        log.exception("Falha ao enviar WhatsApp via Twilio API")
        return False

# =========================
# Rota principal do WhatsApp
# =========================
@bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Webhook principal do WhatsApp com todas as funcionalidades integradas"""
    
    # Extrair dados da mensagem
    from_number = request.form.get("From", "").replace("whatsapp:", "")
    user_message = request.form.get("Body", "").strip()
    
    if not from_number or not user_message:
        return Response("", status=200)
    
    log.info(f"Mensagem recebida de {from_number}: {user_message}")
    
    try:
        # 1. Registrar a mensagem de entrada
        lead_manager.add_interaction(from_number, "Entrada", user_message)
        
        # 2. Extrair informações do cliente se disponíveis
        client_info = ai_humanizer.extract_client_info(user_message)
        if client_info:
            lead_manager.create_or_update_lead(from_number, **client_info)
        
        # 3. Verificar se deve pedir informações
        info_request = ai_humanizer.should_ask_for_info(from_number)
        
        # 4. Tentar responder com catálogo primeiro
        catalog_response = tentar_responder_com_catalogo(user_message, current_app.config.get("OFFERS_PATH", ""))
        
        if catalog_response:
            # Usar resposta do catálogo mas humanizar
            ai_response = catalog_response
        else:
            # 5. Gerar resposta humanizada com IA
            enhanced_prompt = ai_humanizer.create_enhanced_prompt(user_message, from_number)
            
            # Chamar OpenAI
            client = current_app.config.get("OPENAI_CLIENT")
            if client:
                try:
                    response = client.chat.completions.create(
                        model=current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=[
                            {"role": "system", "content": enhanced_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    ai_response = response.choices[0].message.content.strip()
                except Exception as e:
                    log.error(f"Erro na API OpenAI: {e}")
                    ai_response = "Desculpe, estou com dificuldades técnicas no momento. Pode tentar novamente em alguns minutos?"
            else:
                ai_response = "Olá! Obrigado por entrar em contato. Como posso ajudá-lo hoje?"
        
        # 6. Adicionar toques humanos à resposta
        final_response = ai_humanizer.add_human_touches(ai_response)
        
        # 7. Adicionar pedido de informações se necessário
        if info_request and len(final_response) < 800:  # Não sobrecarregar a mensagem
            final_response += f"\n\n{info_request}"
        
        # 8. Registrar a resposta
        lead_manager.add_interaction(from_number, "Saída", final_response)
        
        # 9. Tentar enviar via Twilio se configurado
        if current_app.config.get("FORCE_TWILIO_API_REPLY"):
            send_via_twilio_api(from_number, final_response)
        
        # 10. Retornar resposta TwiML
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{xml_escape(final_response)}</Message>
</Response>"""
        
        return Response(twiml_response, mimetype="application/xml")
        
    except Exception as e:
        log.error(f"Erro no webhook WhatsApp: {e}")
        error_response = "Desculpe, ocorreu um erro interno. Nossa equipe foi notificada."
        
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{xml_escape(error_response)}</Message>
</Response>"""
        
        return Response(twiml_response, mimetype="application/xml")

# =========================
# Painel Kanban
# =========================
@bp.route("/painel")
def painel_kanban():
    """Painel Kanban moderno para gestão de leads"""
    
    # Obter todos os leads
    all_leads = lead_manager.get_all_leads()
    
    # Organizar por status
    statuses = [
        {
            "id": "novo",
            "name": "Novo",
            "class": "status-novo",
            "icon": "fas fa-user-plus",
            "leads": [],
            "count": 0
        },
        {
            "id": "em-atendimento",
            "name": "Em Atendimento",
            "class": "status-em-atendimento",
            "icon": "fas fa-comments",
            "leads": [],
            "count": 0
        },
        {
            "id": "proposta-enviada",
            "name": "Proposta Enviada",
            "class": "status-proposta-enviada",
            "icon": "fas fa-file-alt",
            "leads": [],
            "count": 0
        },
        {
            "id": "agendado",
            "name": "Agendado",
            "class": "status-agendado",
            "icon": "fas fa-calendar-check",
            "leads": [],
            "count": 0
        },
        {
            "id": "vendido",
            "name": "Vendido",
            "class": "status-vendido",
            "icon": "fas fa-trophy",
            "leads": [],
            "count": 0
        },
        {
            "id": "perdido",
            "name": "Perdido",
            "class": "status-perdido",
            "icon": "fas fa-times-circle",
            "leads": [],
            "count": 0
        }
    ]
    
    # Mapear status para IDs
    status_map = {
        "Novo": "novo",
        "Em Atendimento": "em-atendimento",
        "Proposta Enviada": "proposta-enviada",
        "Agendado": "agendado",
        "Vendido": "vendido",
        "Perdido": "perdido"
    }
    
    # Distribuir leads por status
    for lead in all_leads:
        lead_status = lead.get("status", "Novo")
        status_id = status_map.get(lead_status, "novo")
        
        # Formatar data da última interação
        try:
            last_interaction = datetime.fromisoformat(lead.get("ultima_interacao", ""))
            lead["ultima_interacao_formatted"] = last_interaction.strftime("%d/%m %H:%M")
        except:
            lead["ultima_interacao_formatted"] = "N/A"
        
        # Encontrar o status correto e adicionar o lead
        for status in statuses:
            if status["id"] == status_id:
                status["leads"].append(lead)
                status["count"] += 1
                break
    
    # Calcular métricas
    total_leads = len(all_leads)
    converted = len([l for l in all_leads if l.get("status") == "Vendido"])
    conversion_rate = round((converted / total_leads) * 100, 1) if total_leads > 0 else 0
    
    return render_template("painel_kanban.html", 
                         statuses=statuses,
                         total_leads=total_leads,
                         conversion_rate=conversion_rate)

# =========================
# APIs para o painel
# =========================
@bp.route("/api/update-lead-status", methods=["POST"])
def update_lead_status():
    """API para atualizar status do lead"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        new_status = data.get("status")
        
        if not phone or not new_status:
            return jsonify({"success": False, "error": "Dados incompletos"})
        
        lead = lead_manager.update_status(phone, new_status)
        
        if lead:
            return jsonify({"success": True, "lead": lead})
        else:
            return jsonify({"success": False, "error": "Lead não encontrado"})
            
    except Exception as e:
        log.error(f"Erro ao atualizar status: {e}")
        return jsonify({"success": False, "error": str(e)})

@bp.route("/api/lead-details/<path:phone>")
def get_lead_details(phone):
    """API para obter detalhes do lead"""
    try:
        lead = lead_manager.get_lead(phone)
        
        if lead:
            return jsonify({"success": True, "lead": lead})
        else:
            return jsonify({"success": False, "error": "Lead não encontrado"})
            
    except Exception as e:
        log.error(f"Erro ao obter detalhes do lead: {e}")
        return jsonify({"success": False, "error": str(e)})

@bp.route("/api/add-note", methods=["POST"])
def add_note():
    """API para adicionar nota ao lead"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        note = data.get("note")
        
        if not phone or not note:
            return jsonify({"success": False, "error": "Dados incompletos"})
        
        lead = lead_manager.add_note(phone, note, "Vendedor")
        
        if lead:
            return jsonify({"success": True, "lead": lead})
        else:
            return jsonify({"success": False, "error": "Lead não encontrado"})
            
    except Exception as e:
        log.error(f"Erro ao adicionar nota: {e}")
        return jsonify({"success": False, "error": str(e)})

@bp.route("/api/send-message", methods=["POST"])
def send_manual_message():
    """API para enviar mensagem manual"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        message = data.get("message")
        
        if not phone or not message:
            return jsonify({"success": False, "error": "Dados incompletos"})
        
        # Registrar mensagem
        lead_manager.add_interaction(phone, "Saída", message, "manual")
        
        # Tentar enviar via Twilio
        success = send_via_twilio_api(phone, message)
        
        return jsonify({"success": True, "sent_via_twilio": success})
        
    except Exception as e:
        log.error(f"Erro ao enviar mensagem: {e}")
        return jsonify({"success": False, "error": str(e)})

@bp.route("/api/analytics")
def get_analytics():
    """API para obter analytics"""
    try:
        analytics = analytics_engine.generate_full_report()
        return jsonify({"success": True, "analytics": analytics})
        
    except Exception as e:
        log.error(f"Erro ao gerar analytics: {e}")
        return jsonify({"success": False, "error": str(e)})

# =========================
# Rotas de agendamento
# =========================
@bp.route("/api/available-slots/<date>")
def get_available_slots_api(date):
    """API para obter horários disponíveis"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        slots = get_available_slots(target_date)
        
        formatted_slots = []
        for slot in slots:
            formatted_slots.append({
                "datetime": slot.isoformat(),
                "time": slot.strftime("%H:%M"),
                "formatted": slot.strftime("%d/%m às %H:%M")
            })
        
        return jsonify({"success": True, "slots": formatted_slots})
        
    except Exception as e:
        log.error(f"Erro ao obter horários disponíveis: {e}")
        return jsonify({"success": False, "error": str(e)})

@bp.route("/api/schedule-appointment", methods=["POST"])
def schedule_appointment():
    """API para agendar test drive"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        datetime_str = data.get("datetime")
        client_name = data.get("client_name", "Cliente")
        
        if not phone or not datetime_str:
            return jsonify({"success": False, "error": "Dados incompletos"})
        
        # Converter datetime
        appointment_time = datetime.fromisoformat(datetime_str)
        
        # Verificar disponibilidade
        if not is_slot_available(appointment_time):
            return jsonify({"success": False, "error": "Horário não disponível"})
        
        # Criar evento no calendário
        event_title = f"Test Drive - {client_name}"
        event_description = f"Test drive agendado via WhatsApp\nCliente: {client_name}\nTelefone: {phone}"
        
        event_id = create_event(event_title, appointment_time, 60, None, event_description)
        
        if event_id:
            # Atualizar status do lead
            lead_manager.update_status(phone, "Agendado")
            
            # Adicionar nota sobre o agendamento
            note = f"Test drive agendado para {appointment_time.strftime('%d/%m/%Y às %H:%M')}"
            lead_manager.add_note(phone, note, "Sistema")
            
            return jsonify({"success": True, "event_id": event_id})
        else:
            return jsonify({"success": False, "error": "Erro ao criar evento no calendário"})
            
    except Exception as e:
        log.error(f"Erro ao agendar: {e}")
        return jsonify({"success": False, "error": str(e)})

# =========================
# Inicialização da automação
# =========================
@bp.record_once
def _start_automation(setup_state):
    """Inicia o motor de automação quando o blueprint é registrado"""
    try:
        automation_engine.start_automation()
        log.info("Motor de automação iniciado com sucesso")
    except Exception as e:
        log.error(f"Erro ao iniciar automação: {e}")

# =========================
# Rota de teste com dados fictícios
# =========================
@bp.route("/criar-dados-teste")
def criar_dados_teste():
    """Cria dados de teste para demonstração"""
    
    # Dados de teste
    test_leads = [
        {
            "phone": "+5547999111111",
            "nome": "João Silva",
            "email": "joao@email.com",
            "status": "Novo",
            "messages": [
                ("Entrada", "Oi, gostaria de saber sobre o Fiat Pulse"),
                ("Saída", "Olá João! O Pulse é um excelente SUV. Você prefere a versão manual ou automática?"),
                ("Entrada", "Automática. Qual o preço?")
            ]
        },
        {
            "phone": "+5547999222222",
            "nome": "Maria Santos",
            "email": "maria@email.com",
            "status": "Em Atendimento",
            "messages": [
                ("Entrada", "Quero fazer test drive do Toro"),
                ("Saída", "Ótima escolha! Quando você gostaria de agendar?"),
                ("Entrada", "Amanhã de manhã se possível")
            ]
        },
        {
            "phone": "+5547999333333",
            "nome": "Carlos Lima",
            "status": "Proposta Enviada",
            "messages": [
                ("Entrada", "Preciso de financiamento para o Argo"),
                ("Saída", "Claro! Vou preparar uma simulação. Qual valor de entrada você tem disponível?"),
                ("Entrada", "Uns 15 mil"),
                ("Saída", "Perfeito! Te enviei uma proposta por email. O que achou?")
            ]
        }
    ]
    
    # Criar leads de teste
    for test_lead in test_leads:
        # Criar lead
        lead = lead_manager.create_or_update_lead(
            test_lead["phone"],
            nome_cliente=test_lead["nome"],
            email=test_lead.get("email", ""),
            status=test_lead["status"]
        )
        
        # Adicionar mensagens
        for direction, message in test_lead["messages"]:
            lead_manager.add_interaction(test_lead["phone"], direction, message)
    
    return jsonify({"success": True, "message": "Dados de teste criados com sucesso!"})

# Manter compatibilidade com rotas antigas
@bp.route("/painel-antigo")
def painel_antigo():
    """Painel antigo para comparação"""
    # Implementação do painel antigo se necessário
    return "<h1>Painel Antigo</h1><p><a href='/painel'>Ir para o novo painel</a></p>"

