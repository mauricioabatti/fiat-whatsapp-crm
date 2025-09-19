# routes.py - VERSÃO CORRETA COM TODAS AS FUNCIONALIDADES
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

# ========================
# Twilio helpers (envio via API)
# ========================
def _twilio_client():
    sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    token = current_app.config.get("TWILIO_AUTH_TOKEN")
    if not (sid and token): return None
    try:
        client = TwilioClient(sid, token)
        if not client: return False
        return client
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

@bp.route("/whatsapp", methods=["GET"])
def whatsapp_test():
    return "Webhook WhatsApp funcionando! Use POST para enviar mensagens."


# ========================
# Rota principal do WhatsApp
# ========================
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
        
        # 2. Gerar resposta humanizada
        response_text = ai_humanizer.generate_response(from_number, user_message)
        
        # 3. Enviar resposta
        if response_text:
            success = send_via_twilio_api(from_number, response_text)
            if success:
                lead_manager.add_interaction(from_number, "Saída", response_text)
        
        return Response("", status=200)
        
    except Exception as e:
        log.exception(f"Erro no webhook WhatsApp: {e}")
        return Response("", status=500)

# ========================
# Painel Kanban
# ========================
@bp.route("/painel")
def painel_kanban():
    """Painel visual Kanban para gestão de leads"""
    try:
        leads = lead_manager.get_all_leads()
        
        # Organizar leads por status
        leads_por_status = {
            'Novo': [],
            'Em Atendimento': [],
            'Proposta Enviada': [],
            'Agendado': [],
            'Vendido': [],
            'Perdido': []
        }
        
        for lead in leads:
            status = lead.get('status', 'Novo')
            if status in leads_por_status:
                leads_por_status[status].append(lead)
        
        return render_template('painel_kanban.html', leads_por_status=leads_por_status)
        
    except Exception as e:
        log.exception(f"Erro no painel: {e}")
        return f"Erro: {e}", 500

@bp.route("/api/leads")
def api_leads():
    """API para obter todos os leads"""
    try:
        leads = lead_manager.get_all_leads()
        return jsonify(leads)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/api/lead/<phone>/status", methods=["POST"])
def update_lead_status(phone):
    """Atualizar status de um lead"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status:
            lead_manager.update_lead_status(phone, new_status)
            return jsonify({"success": True})
        
        return jsonify({"error": "Status não fornecido"}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/api/send-message", methods=["POST"])
def send_manual_message():
    """Enviar mensagem manual para um lead"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        message = data.get('message')
        
        if phone and message:
            success = send_via_twilio_api(phone, message)
            if success:
                lead_manager.add_interaction(phone, "Saída Manual", message)
                return jsonify({"success": True})
        
        return jsonify({"error": "Dados incompletos"}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================
# Dados de teste
# ========================
@bp.route("/criar-dados-teste")
def criar_dados_teste():
    """Criar leads de exemplo para demonstração"""
    try:
        leads_exemplo = [
            {
                "phone": "+5547999111111",
                "nome_cliente": "João Silva",
                "status": "Novo",
                "interesse": "Fiat Argo",
                "ultima_interacao": datetime.now().isoformat()
            },
            {
                "phone": "+5547999222222", 
                "nome_cliente": "Maria Santos",
                "status": "Em Atendimento",
                "interesse": "Fiat Toro",
                "ultima_interacao": datetime.now().isoformat()
            },
            {
                "phone": "+5547999333333",
                "nome_cliente": "Pedro Costa",
                "status": "Proposta Enviada", 
                "interesse": "Fiat Pulse",
                "ultima_interacao": datetime.now().isoformat()
            }
        ]
        
        for lead in leads_exemplo:
            lead_manager.create_or_update_lead(
                lead["phone"],
                nome_cliente=lead["nome_cliente"],
                status=lead["status"]
            )
            lead_manager.add_interaction(
                lead["phone"], 
                "Entrada", 
                f"Olá, tenho interesse no {lead['interesse']}"
            )
        
        return jsonify({
            "success": True, 
            "message": f"Criados {len(leads_exemplo)} leads de exemplo",
            "leads": leads_exemplo
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================
# Relatórios e Analytics
# ========================
@bp.route("/relatorios")
def relatorios():
    """Página de relatórios e analytics"""
    try:
        analytics = analytics_engine.generate_report()
        return render_template('relatorios.html', analytics=analytics)
    except Exception as e:
        return f"Erro: {e}", 500

@bp.route("/api/analytics")
def api_analytics():
    """API para dados de analytics"""
    try:
        analytics = analytics_engine.generate_report()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

