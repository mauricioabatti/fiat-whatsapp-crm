# calendar_helpers.py - VERSÃO CORRIGIDA
import os
import json
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from zoneinfo import ZoneInfo

log = logging.getLogger("fiat-whatsapp")

def build_gcal():
    """Constrói cliente do Google Calendar com credenciais corretas"""
    try:
        # Usar arquivo de credenciais local
        credentials_file = "google_credentials.json"
        
        if not os.path.exists(credentials_file):
            log.error("Arquivo de credenciais não encontrado")
            return None
        
        with open(credentials_file, 'r') as f:
            credentials_info = json.load(f)
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        log.info("Cliente Google Calendar criado com sucesso")
        return service
        
    except Exception as e:
        log.error(f"Erro ao criar cliente Google Calendar: {e}")
        return None

def get_calendar_id():
    """Retorna o ID do calendário configurado"""
    return "2999dd11ac14bbf95f5e041e85724234a36fa67a3b43aa366cdb20b5f061c35f@group.calendar.google.com"

def is_slot_available(start_datetime: datetime, duration_minutes: int = 60) -> bool:
    """Verifica se um horário está disponível no calendário"""
    service = build_gcal()
    if not service:
        return False
    
    try:
        calendar_id = get_calendar_id()
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Consultar disponibilidade
        freebusy_query = {
            'timeMin': start_datetime.isoformat(),
            'timeMax': end_datetime.isoformat(),
            'items': [{'id': calendar_id}]
        }
        
        result = service.freebusy().query(body=freebusy_query).execute()
        busy_times = result.get('calendars', {}).get(calendar_id, {}).get('busy', [])
        
        # Se não há períodos ocupados, está disponível
        return len(busy_times) == 0
        
    except Exception as e:
        log.error(f"Erro ao verificar disponibilidade: {e}")
        return False

def create_event(title: str, start_datetime: datetime, duration_minutes: int = 60, 
                attendee_email: str = None, description: str = "") -> Optional[str]:
    """Cria um evento no calendário"""
    service = build_gcal()
    if not service:
        return None
    
    try:
        calendar_id = get_calendar_id()
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Configurar timezone
        tz = ZoneInfo("America/Sao_Paulo")
        
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_datetime.replace(tzinfo=tz).isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_datetime.replace(tzinfo=tz).isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
        }
        
        if attendee_email:
            event['attendees'] = [{'email': attendee_email}]
        
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        event_id = created_event.get('id')
        log.info(f"Evento criado com sucesso: {event_id}")
        return event_id
        
    except Exception as e:
        log.error(f"Erro ao criar evento: {e}")
        return None

def freebusy(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Retorna períodos ocupados no calendário"""
    service = build_gcal()
    if not service:
        return []
    
    try:
        calendar_id = get_calendar_id()
        
        freebusy_query = {
            'timeMin': start_date.isoformat() + 'Z',
            'timeMax': end_date.isoformat() + 'Z',
            'items': [{'id': calendar_id}]
        }
        
        result = service.freebusy().query(body=freebusy_query).execute()
        busy_times = result.get('calendars', {}).get(calendar_id, {}).get('busy', [])
        
        return busy_times
        
    except Exception as e:
        log.error(f"Erro ao consultar períodos ocupados: {e}")
        return []

def business_hours_for(date: datetime) -> List[Tuple[time, time]]:
    """Retorna horários de funcionamento para uma data"""
    weekday = date.weekday()  # 0 = segunda, 6 = domingo
    
    if weekday < 5:  # Segunda a sexta
        return [(time(8, 30), time(18, 30))]
    elif weekday == 5:  # Sábado
        return [(time(8, 30), time(12, 30))]
    else:  # Domingo
        return []  # Fechado

def get_available_slots(date: datetime, duration_minutes: int = 60) -> List[datetime]:
    """Retorna horários disponíveis para uma data específica"""
    available_slots = []
    
    # Obter horários de funcionamento
    business_hours = business_hours_for(date)
    if not business_hours:
        return available_slots
    
    # Obter períodos ocupados
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    busy_periods = freebusy(start_of_day, end_of_day)
    
    for start_time, end_time in business_hours:
        current_time = date.replace(hour=start_time.hour, minute=start_time.minute)
        end_business = date.replace(hour=end_time.hour, minute=end_time.minute)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_business:
            # Verificar se o slot está livre
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            is_free = True
            for busy_period in busy_periods:
                busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                
                # Converter para timezone local se necessário
                if busy_start.tzinfo:
                    busy_start = busy_start.astimezone(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
                    busy_end = busy_end.astimezone(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
                
                # Verificar sobreposição
                if (current_time < busy_end and slot_end > busy_start):
                    is_free = False
                    break
            
            if is_free:
                available_slots.append(current_time)
            
            # Avançar 30 minutos
            current_time += timedelta(minutes=30)
    
    return available_slots

def format_available_times(date: datetime) -> str:
    """Formata horários disponíveis para exibição"""
    slots = get_available_slots(date)
    
    if not slots:
        return "Nenhum horário disponível nesta data."
    
    formatted_slots = []
    for slot in slots[:6]:  # Mostrar apenas os primeiros 6 horários
        formatted_slots.append(slot.strftime("%H:%M"))
    
    return "Horários disponíveis: " + ", ".join(formatted_slots)
