"""
CNJ API Client - Serventias Extrajudiciais
Cliente para integração com a API SOAP do CNJ (Conselho Nacional de Justiça)
"""

import streamlit as st
from zeep import Client
from zeep.exceptions import Fault, TransportError
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CNJClient:
    """Cliente para API SOAP do CNJ - Serventias Extrajudiciais"""
    
    def __init__(self, timeout=30):
        self.wsdl_url = "https://www.cnj.jus.br/corregedoria/ws/extraJudicial.php?wsdl"
        self.timeout = timeout
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa o cliente SOAP com timeout"""
        try:
            from zeep.transports import Transport
            from requests import Session
            
            session = Session()
            session.timeout = self.timeout
            transport = Transport(session=session)
            
            self.client = Client(self.wsdl_url, transport=transport)
            logger.info(f"Cliente CNJ inicializado com timeout de {self.timeout}s")
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente CNJ: {e}")
            raise
    
    
    def buscar_serventias_ativas(self, dt_inicio: str, dt_final: str, uf: str = "RJ"):
        """
        Busca serventias ativas em um período
        
        Args:
            dt_inicio: Data inicial (formato: DD/MM/YYYY)
            dt_final: Data final (formato: DD/MM/YYYY)
            uf: Sigla da UF (padrão: RJ)
        
        Returns:
            DataFrame com dados das serventias
        """
        try:
            logger.info(f"Buscando serventias ativas: {dt_inicio} a {dt_final}, UF: {uf}")
            
            response = self.client.service.servico(
                dt_inicio=dt_inicio,
                dt_final=dt_final,
                ind_uf=uf
            )
            
            return self._parse_response(response)
            
        except Fault as fault:
            logger.error(f"SOAP Fault: {fault}")
            raise Exception(f"Erro na API CNJ: {fault.message}")
        except TransportError as error:
            logger.error(f"Transport Error: {error}")
            raise Exception("Erro de conexão com a API CNJ")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise
    
    def buscar_inclusoes(self, dia: str, mes: str, ano: str, uf: str = "RJ"):
        """
        Busca serventias incluídas em um período
        
        Args:
            dia: Dia (01-31)
            mes: Mês (01-12)
            ano: Ano (YYYY)
            uf: Sigla da UF
        
        Returns:
            DataFrame com serventias incluídas
        """
        try:
            logger.info(f"Buscando inclusões: {dia}/{mes}/{ano}, UF: {uf}")
            
            response = self.client.service.servico_atualizacao_inclusao(
                dia=dia,
                mes=mes,
                ano=ano,
                ind_uf=uf
            )
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Erro ao buscar inclusões: {e}")
            raise
    
    def buscar_alteracoes(self, dia: str, mes: str, ano: str, uf: str = "RJ"):
        """
        Busca serventias alteradas em um período
        
        Args:
            dia: Dia (01-31)
            mes: Mês (01-12)
            ano: Ano (YYYY)
            uf: Sigla da UF
        
        Returns:
            DataFrame com serventias alteradas
        """
        try:
            logger.info(f"Buscando alterações: {dia}/{mes}/{ano}, UF: {uf}")
            
            response = _self.client.service.servico_atualizacao_alteracao(
                dia=dia,
                mes=mes,
                ano=ano,
                ind_uf=uf
            )
            
            return _self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Erro ao buscar alterações: {e}")
            raise
    
    def _parse_response(self, response):
        """
        Converte resposta XML da API para DataFrame
        
        Args:
            response: Objeto de resposta do SOAP ou string XML
        
        Returns:
            DataFrame pandas com dados parseados
        """
        try:
            # A resposta pode vir de duas formas:
            # 1. Objeto com campo 'serventias'
            # 2. String XML diretamente
            
            if hasattr(response, 'serventias'):
                xml_string = response.serventias
            elif isinstance(response, str):
                xml_string = response
            else:
                # Tenta converter para string
                xml_string = str(response)
            
            logger.info(f"Tipo de resposta: {type(response)}")
            logger.info(f"Tamanho XML: {len(xml_string)} caracteres")
            
            # Verifica se tem conteúdo
            if not xml_string or len(xml_string.strip()) == 0:
                logger.warning("Resposta vazia da API")
                return pd.DataFrame()
            
            # Sanitização do XML (Correção de problemas comuns da API CNJ)
            xml_string = self._sanitize_xml(xml_string)
            
            # Parse do XML
            root = ET.fromstring(xml_string)
            
            # Extrai dados de cada serventia (tag ROW)
            serventias_data = []
            
            # Mapping de Atribuições CNJ
            # 1: Notas, 2: Protesto, 3: Imóveis, 4: RTD, 5: RCPJ, 6: RCPN, 7: Distribuidor
            ATTRIBUTION_MAP = {
                '1': 'Notas',
                '2': 'Protesto',
                '3': 'Registro de Imóveis',
                '4': 'RTD',
                '5': 'RCPJ',
                '6': 'RCPN',
                '7': 'Distribuidor',
                '8': 'Contratos Marítimos'
            }
            
            for row in root.findall('.//ROW'):
                serventia_dict = {}
                
                # Extrai todos os elementos filhos
                for child in row:
                    tag_name = child.tag.lower()
                    
                    # Tratamento especial para tags aninhadas (Ex: ATRIBUICAO -> ID_ATRIBUICAO)
                    if len(child) > 0:
                        if tag_name == 'atribuicao':
                            # Coleta todos os IDs de atribuição
                            ids = [gc.text for gc in child if gc.text]
                            # Mapeia para nomes legíveis
                            nomes = [ATTRIBUTION_MAP.get(i.strip(), i) for i in ids]
                            # Junta com vírgula (ex: "Notas, Protesto")
                            serventia_dict[tag_name] = ", ".join(nomes)
                        else:
                            # Caso genérico para outras listas
                            values = [gc.text for gc in child if gc.text]
                            serventia_dict[tag_name] = ", ".join(values)
                    else:
                         serventia_dict[tag_name] = child.text
                
                serventias_data.append(serventia_dict)
            
            # Converte para DataFrame
            df = pd.DataFrame(serventias_data)
            
            logger.info(f"Parseados {len(df)} registros")
            
            return df
            
        except ET.ParseError as e:
            logger.error(f"Erro ao parsear XML: {e}")
            logger.error(f"XML recebido: {xml_string[:500] if 'xml_string' in locals() else 'N/A'}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            logger.error(f"Tipo de resposta: {type(response)}")
            return pd.DataFrame()
    
    def formatar_data(self, data: datetime) -> str:
        """
        Formata data para o padrão da API (DD/MM/YYYY)
        
        Args:
            data: Objeto datetime
        
        Returns:
            String formatada
        """
        return data.strftime("%d/%m/%Y")

    def _sanitize_xml(self, xml_string: str) -> str:
        """
        Limpa e corrige problemas comuns no XML retornado pela API
        """
        if not xml_string:
            return ""
            
        # 1. Remove caracteres de controle inválidos (exceto tab, line feed, carriage return)
        import re
        xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_string)
        
        # 2. Tenta corrigir & não escapado (comum em nomes de empresas/cartórios)
        # Regex busca & que NÃO é seguido por (amp|lt|gt|quot|apos|#\d+);
        xml_string = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+);)', '&amp;', xml_string)
        
        return xml_string


# Funções auxiliares para uso direto
@st.cache_resource
def get_cnj_client():
    """Retorna instância singleton do cliente CNJ"""
    return CNJClient()


def buscar_serventias_rj(dt_inicio: str, dt_final: str):
    """
    Atalho para buscar serventias do RJ
    
    Args:
        dt_inicio: Data inicial (DD/MM/YYYY)
        dt_final: Data final (DD/MM/YYYY)
    
    Returns:
        DataFrame com serventias
    """
    client = get_cnj_client()
    return client.buscar_serventias_ativas(dt_inicio, dt_final, "RJ")
