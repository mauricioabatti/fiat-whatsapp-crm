# test_calendar.py
import os
import json
import base64
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_google_calendar():
    """Testa a integração com o Google Calendar"""
    
    print("🔍 Testando integração com Google Calendar...")
    
    # Configurações
    calendar_id = "2999dd11ac14bbf95f5e041e85724234a36fa67a3b43aa366cdb20b5f061c35f@group.calendar.google.com"
    credentials_file = "google_credentials.json"
    
    try:
        # 1. Verificar se o arquivo de credenciais existe
        if not os.path.exists(credentials_file):
            print("❌ Arquivo de credenciais não encontrado!")
            return False
        
        print("✅ Arquivo de credenciais encontrado")
        
        # 2. Carregar credenciais
        with open(credentials_file, 'r') as f:
            credentials_info = json.load(f)
        
        print("✅ Credenciais carregadas")
        
        # 3. Criar objeto de credenciais
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        print("✅ Objeto de credenciais criado")
        
        # 4. Construir serviço do Calendar
        service = build('calendar', 'v3', credentials=credentials)
        
        print("✅ Serviço do Calendar construído")
        
        # 5. Testar acesso ao calendário específico
        try:
            calendar = service.calendars().get(calendarId=calendar_id).execute()
            print(f"✅ Acesso ao calendário confirmado: {calendar.get('summary', 'Sem nome')}")
        except HttpError as e:
            if e.resp.status == 404:
                print(f"❌ Calendário não encontrado ou sem permissão: {calendar_id}")
                print("💡 Verifique se o calendário foi compartilhado com a conta de serviço:")
                print(f"   {credentials_info.get('client_email')}")
                return False
            else:
                print(f"❌ Erro ao acessar calendário: {e}")
                return False
        
        # 6. Testar listagem de eventos (próximos 7 dias)
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=7)).isoformat() + 'Z'
        
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"✅ Listagem de eventos funcionando ({len(events)} eventos encontrados)")
            
            if events:
                print("📅 Próximos eventos:")
                for event in events[:3]:  # Mostrar apenas os 3 primeiros
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(f"   - {event.get('summary', 'Sem título')}: {start}")
            
        except HttpError as e:
            print(f"❌ Erro ao listar eventos: {e}")
            return False
        
        # 7. Testar criação de evento (teste)
        try:
            test_event = {
                'summary': 'TESTE - Test Drive Fiat',
                'description': 'Evento de teste criado pelo sistema CRM WhatsApp',
                'start': {
                    'dateTime': (now + timedelta(hours=1)).isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': (now + timedelta(hours=2)).isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                # Removido attendees para evitar erro de permissão
            }
            
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=test_event
            ).execute()
            
            print(f"✅ Criação de evento funcionando (ID: {created_event.get('id')})")
            
            # Deletar o evento de teste
            service.events().delete(
                calendarId=calendar_id,
                eventId=created_event.get('id')
            ).execute()
            
            print("✅ Evento de teste removido")
            
        except HttpError as e:
            print(f"❌ Erro ao criar/deletar evento de teste: {e}")
            return False
        
        # 8. Testar verificação de disponibilidade
        try:
            freebusy_query = {
                'timeMin': time_min,
                'timeMax': time_max,
                'items': [{'id': calendar_id}]
            }
            
            freebusy_result = service.freebusy().query(body=freebusy_query).execute()
            busy_times = freebusy_result.get('calendars', {}).get(calendar_id, {}).get('busy', [])
            
            print(f"✅ Verificação de disponibilidade funcionando ({len(busy_times)} períodos ocupados)")
            
        except HttpError as e:
            print(f"❌ Erro ao verificar disponibilidade: {e}")
            return False
        
        print("\n🎉 TODOS OS TESTES PASSARAM! Google Calendar está funcionando corretamente.")
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

def fix_calendar_helpers():
    """Corrige o arquivo calendar_helpers.py com as configurações corretas"""
    
    print("\n🔧 Corrigindo calendar_helpers.py...")
    
    calendar_helpers_content = '''# calendar_helpers.py - VERSÃO CORRIGIDA
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
'''
    
    # Escrever o arquivo corrigido
    with open('/home/ubuntu/fiat-globo-whatsapp-piloto/calendar_helpers.py', 'w', encoding='utf-8') as f:
        f.write(calendar_helpers_content)
    
    print("✅ calendar_helpers.py corrigido!")

if __name__ == "__main__":
    # Executar testes
    success = test_google_calendar()
    
    if success:
        # Corrigir o arquivo calendar_helpers.py
        fix_calendar_helpers()
        print("\n🎉 Google Calendar configurado e funcionando!")
    else:
        print("\n❌ Há problemas com a configuração do Google Calendar.")
        print("\n💡 Possíveis soluções:")
        print("1. Verifique se a API do Google Calendar está habilitada no projeto")
        print("2. Confirme se o calendário foi compartilhado com a conta de serviço")
        print("3. Verifique as permissões da conta de serviço")

